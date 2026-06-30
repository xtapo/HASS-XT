import os
import time
import base64
import requests
import datetime
import threading
import hashlib
import cv2
import numpy as np
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

def detect_motion(image_bytes_1: bytes, image_bytes_2: bytes, threshold: float = 2.0) -> Tuple[bool, float]:
    try:
        nparr1 = np.frombuffer(image_bytes_1, np.uint8)
        img1 = cv2.imdecode(nparr1, cv2.IMREAD_GRAYSCALE)
        
        nparr2 = np.frombuffer(image_bytes_2, np.uint8)
        img2 = cv2.imdecode(nparr2, cv2.IMREAD_GRAYSCALE)
        
        if img1 is None or img2 is None:
            print("[Scanner] Failed to decode images for motion detection. Defaulting to motion detected.")
            return True, 100.0
            
        if img1.shape != img2.shape:
            print(f"[Scanner] Image dimensions mismatch: {img1.shape} vs {img2.shape}. Defaulting to motion detected.")
            return True, 100.0
            
        img1_blur = cv2.GaussianBlur(img1, (21, 21), 0)
        img2_blur = cv2.GaussianBlur(img2, (21, 21), 0)
        
        diff = cv2.absdiff(img1_blur, img2_blur)
        
        _, thresh = cv2.threshold(diff, 25, 255, cv2.THRESH_BINARY)
        
        non_zero_count = np.count_nonzero(thresh)
        total_pixels = thresh.shape[0] * thresh.shape[1]
        changed_percent = (non_zero_count / total_pixels) * 100.0
        
        has_motion = changed_percent >= threshold
        print(f"[Scanner] Motion detection: {changed_percent:.2f}% pixels changed (threshold: {threshold}%). Motion: {has_motion}")
        return has_motion, changed_percent
    except Exception as e:
        print(f"[Scanner] Exception in motion detection algorithm: {e}. Defaulting to motion detected.")
        return True, 100.0

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
        last_scan_times = {}  # entity_id -> float (timestamp)
        active_threads = {}   # entity_id -> Thread
        
        while self.running:
            try:
                entities = list(config.camera_entities)
                if entities:
                    now = time.time()
                    for entity_id in entities:
                        if not self.running:
                            break
                            
                        # Get custom interval or fallback to global scan_interval
                        settings = config.camera_settings.get(entity_id) if hasattr(config, "camera_settings") else None
                        interval = None
                        if settings:
                            if isinstance(settings, dict):
                                interval = settings.get("scan_interval")
                            else:
                                interval = getattr(settings, "scan_interval", None)
                                
                        if interval is None or interval == 0:
                            interval = config.scan_interval
                        interval = max(5, interval)
                        
                        last_scan = last_scan_times.get(entity_id, 0.0)
                        if now - last_scan >= interval:
                            # Verify if a scan thread is already running for this entity
                            t = active_threads.get(entity_id)
                            if t and t.is_alive():
                                print(f"[Scanner] Previous scan for {entity_id} is still running. Skipping this cycle.")
                                continue
                                
                            last_scan_times[entity_id] = now
                            
                            # Start scanning in a background thread
                            print(f"[Scanner] Starting scan thread for {entity_id} (interval: {interval}s)")
                            scan_thread = threading.Thread(
                                target=self.scan_entity,
                                args=(entity_id, False),
                                daemon=True
                            )
                            active_threads[entity_id] = scan_thread
                            scan_thread.start()
                else:
                    # Sleep a bit if no entities configured
                    time.sleep(1)
            except Exception as e:
                print(f"[Scanner] Error in scanner cycle: {e}")
                
            # Sleep 1 second before checking scheduler again
            time.sleep(1)

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
            # Check for motion to optimize API usage (bypass if forced scan)
            if not force:
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
                                
                            # Resolve threshold
                            settings = config.camera_settings.get(entity_id) if hasattr(config, "camera_settings") else None
                            threshold = None
                            if settings:
                                if isinstance(settings, dict):
                                    threshold = settings.get("motion_threshold")
                                else:
                                    threshold = getattr(settings, "motion_threshold", None)
                            
                            if threshold is None or threshold <= 0:
                                threshold = getattr(config, "motion_threshold", 2.0)
                                
                            has_mov, changed_pct = detect_motion(image_bytes, last_image_bytes, threshold)
                            if not has_mov:
                                print(f"[Scanner] OpenCV: No significant motion detected for {entity_id} ({changed_pct:.2f}% < {threshold}%). Skipping AI call.")
                                return True, f"No change (motion {changed_pct:.2f}% < {threshold}%)", ""
                        except Exception as he:
                            print(f"[Scanner] Error reading last image or running motion detection: {he}")

            # Save image to file
            with open(image_path, "wb") as f:
                f.write(image_bytes)

            # 2. Verify AI base url is set
            if not config.ai_proxy_base_url:
                raise Exception("ai_proxy_base_url is not configured in addon Web UI")

            # 3. Call AI
            settings = config.camera_settings.get(entity_id) if hasattr(config, "camera_settings") else None
            prompt = None
            model = None
            if settings:
                if isinstance(settings, dict):
                    prompt = settings.get("ai_prompt")
                    model = settings.get("ai_model")
                else:
                    prompt = getattr(settings, "ai_prompt", None)
                    model = getattr(settings, "ai_model", None)
                    
            prompt = prompt or config.ai_prompt
            model = model or config.ai_model

            description = call_ai_vision(
                config.ai_proxy_base_url,
                config.ai_api_key,
                model,
                prompt,
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
