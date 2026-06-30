import os
import time
import base64
import requests
import datetime
import threading
import hashlib
from typing import Optional, Tuple
from app.config import config
from app.core.db import HistoryDatabase
from app.ha.mqtt_client import HAMQTTClient

# Global database filepath resolved relative to /data or local
def get_data_dir() -> str:
    if os.path.exists("/data") or os.path.isdir("/data"):
        return "/data"
    return "./data"

data_dir = get_data_dir()
db_path = os.path.join(data_dir, "vision_history.sqlite")
images_dir = os.path.join(data_dir, "images")
db = HistoryDatabase(db_path)

def fetch_entity_image(ha_url: str, ha_token: str, entity_id: str) -> bytes:
    headers = {}
    if ha_token:
        headers["Authorization"] = f"Bearer {ha_token}"
    
    # Clean HA URL
    ha_url = ha_url.rstrip("/")
    
    # 1. If camera entity, try camera_proxy endpoint first
    if entity_id.startswith("camera."):
        proxy_url = f"{ha_url}/api/camera_proxy/{entity_id}"
        try:
            print(f"[Scanner] Requesting camera proxy for {entity_id}: {proxy_url}")
            r = requests.get(proxy_url, headers=headers, timeout=15)
            if r.status_code == 200:
                return r.content
            else:
                print(f"[Scanner] Proxy request returned status {r.status_code} for {entity_id}")
        except Exception as e:
            print(f"[Scanner] Exception calling camera proxy for {entity_id}: {e}")

    # 2. Try fetching states details to get entity_picture
    state_url = f"{ha_url}/api/states/{entity_id}"
    try:
        print(f"[Scanner] Requesting state info for {entity_id}: {state_url}")
        r = requests.get(state_url, headers=headers, timeout=15)
        if r.status_code == 200:
            data = r.json()
            entity_picture = data.get("attributes", {}).get("entity_picture")
            if entity_picture:
                # Handle absolute/relative URLs
                img_url = entity_picture
                if entity_picture.startswith("/"):
                    img_url = f"{ha_url}{entity_picture}"
                
                print(f"[Scanner] Requesting entity picture for {entity_id} at: {img_url}")
                r_img = requests.get(img_url, headers=headers, timeout=15)
                if r_img.status_code == 200:
                    return r_img.content
                else:
                    print(f"[Scanner] Entity picture request returned status {r_img.status_code} for {entity_id}")
            else:
                print(f"[Scanner] No entity_picture attribute found for {entity_id}")
        else:
            print(f"[Scanner] State info request returned status {r.status_code} for {entity_id}")
    except Exception as e:
        print(f"[Scanner] Exception fetching state for {entity_id}: {e}")

    # 3. Fallback proxy check for non-camera if it supports proxy anyway
    if not entity_id.startswith("camera."):
        proxy_url = f"{ha_url}/api/camera_proxy/{entity_id}"
        try:
            r = requests.get(proxy_url, headers=headers, timeout=15)
            if r.status_code == 200:
                return r.content
        except Exception:
            pass

    raise Exception(f"Failed to fetch image for entity {entity_id} from Home Assistant (URL: {ha_url})")

def call_ai_vision(api_url: str, api_key: str, model: str, prompt: str, image_bytes: bytes) -> str:
    # Build endpoint URL:
    # ai_proxy_base_url is e.g. http://homeassistant.local:1236/v1
    # Addon will automatically join with /chat/completions if it doesn't already contain it.
    api_url = api_url.rstrip("/")
    if not api_url.endswith("/chat/completions"):
        api_url = f"{api_url}/chat/completions"
        
    base64_image = base64.b64encode(image_bytes).decode("utf-8")
    
    headers = {
        "Content-Type": "application/json"
    }
    if api_key:
        headers["Authorization"] = f"Bearer {api_key}"
        
    payload = {
        "model": model,
        "messages": [
            {
                "role": "user",
                "content": [
                    {
                        "type": "text",
                        "text": prompt
                    },
                    {
                        "type": "image_url",
                        "image_url": {
                            "url": f"data:image/jpeg;base64,{base64_image}"
                        }
                    }
                ]
            }
        ],
        "stream": False
    }
    
    print(f"[Scanner] Sending vision request to AI Proxy: {api_url} (model: {model})")
    response = requests.post(api_url, headers=headers, json=payload, timeout=45)
    
    if response.status_code == 200:
        try:
            data = response.json()
        except Exception as je:
            raise Exception(f"Lỗi giải mã JSON từ AI Proxy: {je}. Nội dung thô: {response.text[:600]}")
            
        try:
            return data["choices"][0]["message"]["content"]
        except (KeyError, IndexError) as e:
            raise Exception(f"Cấu trúc phản hồi từ OpenAI API không đúng: {e}. Nội dung nhận được: {response.text[:600]}")
    else:
        raise Exception(f"AI Proxy báo lỗi HTTP {response.status_code}: {response.text[:600]}")


def send_telegram_notification(bot_token: str, chat_id: str, description: str, image_bytes: Optional[bytes] = None, entity_id: str = ""):
    if not bot_token or not chat_id:
        return
        
    bot_token = bot_token.strip()
    chat_id = chat_id.strip()
    
    print(f"[Telegram] Sending notification for {entity_id} to chat {chat_id}...")
    
    caption_text = f"🔔 AI Vision: {entity_id}\n\n{description}"
    if len(caption_text) > 1000:
        caption_text = caption_text[:997] + "..."
        
    try:
        if image_bytes:
            url = f"https://api.telegram.org/bot{bot_token}/sendPhoto"
            files = {"photo": ("image.jpg", image_bytes, "image/jpeg")}
            data = {
                "chat_id": chat_id,
                "caption": caption_text
            }
            r = requests.post(url, data=data, files=files, timeout=15)
            if r.status_code == 200:
                print("[Telegram] Photo notification sent successfully!")
                return
            else:
                print(f"[Telegram] Failed to send photo (Status {r.status_code}): {r.text}. Retrying as text message...")
        
        # Fallback to plain text message
        url = f"https://api.telegram.org/bot{bot_token}/sendMessage"
        text_message = f"🔔 AI Vision: {entity_id}\n\n{description}"
        if len(text_message) > 4000:
            text_message = text_message[:3997] + "..."
            
        data = {
            "chat_id": chat_id,
            "text": text_message
        }
        r = requests.post(url, json=data, timeout=15)
        if r.status_code == 200:
            print("[Telegram] Text notification sent successfully!")
        else:
            print(f"[Telegram] Failed to send text message (Status {r.status_code}): {r.text}")
            
    except Exception as e:
        print(f"[Telegram] Error sending notification: {e}")


class VisionScanner:
    def __init__(self, mqtt_client: HAMQTTClient):
        self.mqtt_client = mqtt_client
        self.running = False
        self.thread = None
        self._lock = threading.Lock()

    def start(self):
        with self._lock:
            if not self.running:
                self.running = True
                self.thread = threading.Thread(target=self._run_loop, daemon=True)
                self.thread.start()
                print("[Scanner] VisionScanner background loop started.")

    def stop(self):
        with self._lock:
            self.running = False
            print("[Scanner] VisionScanner background loop stopped.")

    def _run_loop(self):
        # Allow initial system startup and MQTT client connection
        time.sleep(3)
        while self.running:
            try:
                # Capture list to avoid modifications during loop
                entities = list(config.camera_entities)
                if entities:
                    print(f"[Scanner] Starting periodic cycle for {len(entities)} entities: {entities}")
                    for entity_id in entities:
                        if not self.running:
                            break
                        # Process individual entity (background polling, duplicate check active)
                        self.scan_entity(entity_id, force=False)
                        # Small delay between entities to avoid overloading APIs
                        time.sleep(1)
                else:
                    print("[Scanner] No camera entities configured for monitoring.")
            except Exception as e:
                print(f"[Scanner] Error in scanner cycle: {e}")
                
            # Sleep in small increments so we can exit quickly if stopped
            elapsed = 0
            scan_interval = max(5, config.scan_interval)
            while self.running and elapsed < scan_interval:
                time.sleep(1)
                elapsed += 1

    def scan_entity(self, entity_id: str, force: bool = False) -> Tuple[bool, str, str]:
        # Perform a scan for a single entity and publish to MQTT + DB.
        # Returns (success, description, error_message)
        timestamp = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        file_timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
        entity_slug = entity_id.replace(".", "_")
        image_filename = f"{file_timestamp}_{entity_slug}.jpg"
        
        # Resolve token (fall back to env)
        token = config.ha_token
        if not token:
            token = os.getenv("SUPERVISOR_TOKEN", "")

        os.makedirs(images_dir, exist_ok=True)
        image_path = os.path.join(images_dir, image_filename)

        try:
            # 1. Fetch image
            image_bytes = fetch_entity_image(config.ha_url, token, entity_id)
            
            # Check duplicate hash to optimize API usage (bypass if forced scan)
            if not force:
                new_hash = hashlib.md5(image_bytes).hexdigest()
                
                # Check last successful image in DB
                last_successful_file = None
                import sqlite3
                try:
                    with sqlite3.connect(db_path) as conn:
                        conn.row_factory = sqlite3.Row
                        cursor = conn.cursor()
                        cursor.execute("""
                            SELECT image_filename FROM history 
                            WHERE entity_id = ? AND status = 'success' 
                            ORDER BY timestamp DESC LIMIT 1
                        """, (entity_id,))
                        row = cursor.fetchone()
                        if row:
                            last_successful_file = row["image_filename"]
                except Exception as dbe:
                    print(f"[Scanner] Error checking last successful image from DB: {dbe}")
                    
                if last_successful_file:
                    last_image_path = os.path.join(images_dir, last_successful_file)
                    if os.path.exists(last_image_path):
                        try:
                            with open(last_image_path, "rb") as lf:
                                last_image_bytes = lf.read()
                            last_hash = hashlib.md5(last_image_bytes).hexdigest()
                            if new_hash == last_hash:
                                print(f"[Scanner] Image for {entity_id} has not changed since last successful scan. Skipping API call.")
                                return True, "No change (skipped duplicate)", ""
                        except Exception as he:
                            print(f"[Scanner] Error reading last image for hash check: {he}")

            # Save image to file
            with open(image_path, "wb") as f:
                f.write(image_bytes)

            # 2. Verify AI base url is set
            if not config.ai_proxy_base_url:
                raise Exception("ai_proxy_base_url is not configured in addon Web UI")

            # 3. Call AI
            description = call_ai_vision(
                config.ai_proxy_base_url,
                config.ai_api_key,
                config.ai_model,
                config.ai_prompt,
                image_bytes
            )

            # 4. Save to Database
            db.add_entry(
                timestamp=timestamp,
                entity_id=entity_id,
                image_filename=image_filename,
                description=description,
                status="success"
            )

            # 5. Publish to MQTT
            self.mqtt_client.update_sensor_state(
                entity_id=entity_id,
                description=description,
                timestamp=timestamp,
                status="success"
            )
            
            # 6. Send to Telegram if configured
            if config.telegram_bot_token and config.telegram_chat_id:
                send_telegram_notification(
                    bot_token=config.telegram_bot_token,
                    chat_id=config.telegram_chat_id,
                    description=description,
                    image_bytes=image_bytes,
                    entity_id=entity_id
                )
            
            print(f"[Scanner] Successfully processed and published scan for {entity_id}")
            return True, description, ""

        except Exception as e:
            error_msg = str(e)
            print(f"[Scanner] Error scanning entity {entity_id}: {error_msg}")
            
            # Save failure status to database
            db.add_entry(
                timestamp=timestamp,
                entity_id=entity_id,
                image_filename=image_filename if os.path.exists(image_path) else "",
                description="",
                status="error",
                error_message=error_msg
            )
            
            # Publish error to MQTT
            self.mqtt_client.update_sensor_state(
                entity_id=entity_id,
                description="",
                timestamp=timestamp,
                status="error",
                error_message=error_msg
            )
            
            return False, "", error_msg
