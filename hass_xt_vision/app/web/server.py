import os
import requests
from fastapi import FastAPI, Response, Query
from fastapi.responses import JSONResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel
from typing import List, Optional, Dict
from app.config import config, save_config
from app.core.scanner import db, images_dir

APP_VERSION = "2.3.0"

class ConfigUpdateModel(BaseModel):
    ha_url: str
    ha_token: Optional[str] = ""
    camera_entities: List[str]
    camera_settings: Optional[Dict[str, dict]] = {}
    scan_interval: int = 30
    motion_threshold: float = 2.0
    ai_proxy_base_url: str
    ai_api_key: Optional[str] = ""
    ai_model: str
    mqtt_host: str = "core-mosquitto"
    mqtt_port: int = 1883
    mqtt_user: Optional[str] = ""
    mqtt_password: Optional[str] = ""
    mqtt_prefix: str = "ai_vision"
    ai_prompt: str = "Hãy mô tả chi tiết hình ảnh này bằng tiếng Việt."
    telegram_bot_token: Optional[str] = ""
    telegram_chat_id: Optional[str] = ""

class TestAllPayload(BaseModel):
    ha_url: str
    ha_token: Optional[str] = ""
    ai_proxy_base_url: str
    ai_api_key: Optional[str] = ""
    ai_model: str
    mqtt_host: str
    mqtt_port: int = 1883
    mqtt_user: Optional[str] = ""
    mqtt_password: Optional[str] = ""
    telegram_bot_token: Optional[str] = ""
    telegram_chat_id: Optional[str] = ""

def create_app(scanner, mqtt_client) -> FastAPI:
    app = FastAPI(title="HASS-XT AI Vision Entity Describer API", version=APP_VERSION)
    
    @app.get("/api/status")
    async def get_status():
        return {
            "status": "online",
            "version": APP_VERSION,
            "mqtt_connected": mqtt_client.connected,
            "mqtt_status_text": mqtt_client.status_text,
            "prefix": config.mqtt_prefix,
            "monitored_count": len(config.camera_entities)
        }

    @app.get("/api/config")
    async def get_config():
        return {
            "ha_url": config.ha_url,
            "ha_token": config.ha_token,
            "camera_entities": config.camera_entities,
            "camera_settings": getattr(config, "camera_settings", {}),
            "scan_interval": config.scan_interval,
            "motion_threshold": getattr(config, "motion_threshold", 2.0),
            "ai_proxy_base_url": config.ai_proxy_base_url,
            "ai_api_key": config.ai_api_key,
            "ai_model": config.ai_model,
            "mqtt_host": config.mqtt_host,
            "mqtt_port": config.mqtt_port,
            "mqtt_user": config.mqtt_user,
            "mqtt_password": config.mqtt_password,
            "mqtt_prefix": config.mqtt_prefix,
            "ai_prompt": config.ai_prompt,
            "telegram_bot_token": config.telegram_bot_token,
            "telegram_chat_id": config.telegram_chat_id
        }

    @app.post("/api/config")
    async def update_config(payload: ConfigUpdateModel):
        mqtt_changed = (payload.mqtt_host != config.mqtt_host or 
                        payload.mqtt_port != config.mqtt_port or
                        payload.mqtt_user != config.mqtt_user or 
                        payload.mqtt_password != config.mqtt_password or
                        payload.mqtt_prefix != config.mqtt_prefix)

        # Save to file
        save_config(payload.model_dump())

        # Re-apply MQTT if connection parameters changed
        if mqtt_changed and mqtt_client:
            mqtt_client.host = payload.mqtt_host.strip()
            mqtt_client.port = payload.mqtt_port
            mqtt_client.user = payload.mqtt_user.strip() if payload.mqtt_user else ""
            mqtt_client.password = payload.mqtt_password.strip() if payload.mqtt_password else ""
            mqtt_client.prefix = payload.mqtt_prefix.strip()
            mqtt_client.start()
            
        return {"status": "success", "message": "Configuration updated successfully"}

    @app.get("/api/history")
    async def get_history(limit: int = Query(50, ge=1, le=200), offset: int = Query(0, ge=0)):
        entries = db.get_entries(limit=limit, offset=offset)
        return entries

    @app.delete("/api/history/{id}")
    async def delete_history_entry(id: int):
        success = db.delete_entry(id)
        if success:
            return {"status": "success", "message": f"Deleted entry {id}"}
        return JSONResponse(status_code=404, content={"status": "error", "message": "Entry not found"})

    @app.post("/api/history/clear")
    async def clear_history():
        success = db.clear_history()
        if success:
            return {"status": "success", "message": "Cleared history"}
        return JSONResponse(status_code=500, content={"status": "error", "message": "Failed to clear history"})

    @app.post("/api/scan_now")
    async def scan_now(payload: dict):
        entity_id = payload.get("entity_id")
        if not entity_id:
            return JSONResponse(status_code=400, content={"status": "error", "message": "entity_id is required"})
            
        success, description, error_message = scanner.scan_entity(entity_id, force=True)
        if success:
            return {"status": "success", "description": description}
        else:
            return JSONResponse(status_code=500, content={"status": "error", "message": error_message})
    @app.post("/api/test_all")
    async def test_all_connections(payload: TestAllPayload):
        import time
        import threading
        import paho.mqtt.client as mqtt

        # 1. Test Home Assistant API
        ha_status = {"status": "success", "message": "Kết nối HA thành công!"}
        ha_url = payload.ha_url.strip()
        ha_token = payload.ha_token.strip() if payload.ha_token else ""
        if not ha_token:
            ha_token = os.getenv("SUPERVISOR_TOKEN", "")
        
        headers = {}
        if ha_token:
            headers["Authorization"] = f"Bearer {ha_token}"
            
        try:
            url = f"{ha_url.rstrip('/')}/api/"
            r = requests.get(url, headers=headers, timeout=5)
            if r.status_code == 200:
                try:
                    msg = r.json().get("message", "API running.")
                except Exception:
                    msg = "API running."
                ha_status["message"] = f"Kết nối HA thành công! Phản hồi: {msg}"
            elif r.status_code == 401:
                ha_status = {"status": "error", "message": "HA báo lỗi 401: Token không đúng"}
            elif r.status_code == 403:
                ha_status = {"status": "error", "message": "HA báo lỗi 403: Truy cập bị từ chối"}
            else:
                ha_status = {"status": "error", "message": f"Mã HTTP từ HA: {r.status_code}"}
        except requests.exceptions.Timeout:
            ha_status = {"status": "error", "message": "HA Timeout: Hết thời gian chờ (sai URL)"}
        except requests.exceptions.ConnectionError:
            ha_status = {"status": "error", "message": "HA ConnectionError: Không thể kết nối tới IP/Port"}
        except Exception as e:
            ha_status = {"status": "error", "message": f"Lỗi HA: {str(e)}"}

        # 2. Test AI Proxy
        ai_status = {"status": "success", "message": "Kết nối AI Proxy thành công!"}
        ai_url = payload.ai_proxy_base_url.strip()
        ai_key = payload.ai_api_key.strip() if payload.ai_api_key else ""
        ai_model = payload.ai_model.strip()
        
        if not ai_url:
            ai_status = {"status": "error", "message": "Chưa điền AI Proxy Base URL"}
        elif not ai_model:
            ai_status = {"status": "error", "message": "Chưa điền Vision Model Name"}
        else:
            api_url = ai_url.rstrip("/")
            if not api_url.endswith("/chat/completions"):
                api_url = f"{api_url}/chat/completions"
                
            ai_headers = {"Content-Type": "application/json"}
            if ai_key:
                ai_headers["Authorization"] = f"Bearer {ai_key}"
                
            ai_payload = {
                "model": ai_model,
                "messages": [{"role": "user", "content": "ping"}],
                "max_tokens": 5,
                "stream": False
            }
            try:
                r_ai = requests.post(api_url, headers=ai_headers, json=ai_payload, timeout=8)
                if r_ai.status_code == 200:
                    ai_status["message"] = "Kết nối AI Proxy thành công (API phản hồi tốt)"
                elif r_ai.status_code == 401:
                    ai_status = {"status": "error", "message": "AI Proxy báo lỗi 401: API Key không đúng"}
                elif r_ai.status_code == 404:
                    ai_status = {"status": "error", "message": "AI Proxy báo lỗi 404: Không tìm thấy model hoặc sai endpoint"}
                else:
                    ai_status = {"status": "error", "message": f"Mã HTTP từ AI Proxy: {r_ai.status_code}"}
            except requests.exceptions.Timeout:
                ai_status = {"status": "error", "message": "AI Proxy Timeout: Hết thời gian chờ"}
            except requests.exceptions.ConnectionError:
                ai_status = {"status": "error", "message": "AI Proxy ConnectionError: Không thể kết nối IP/URL"}
            except Exception as e:
                ai_status = {"status": "error", "message": f"Lỗi AI Proxy: {str(e)}"}

        # 3. Test MQTT Broker
        mqtt_status = {"status": "success", "message": "Kết nối MQTT Broker thành công!"}
        mqtt_host = payload.mqtt_host.strip()
        mqtt_port = payload.mqtt_port
        mqtt_user = payload.mqtt_user.strip() if payload.mqtt_user else ""
        mqtt_pass = payload.mqtt_password.strip() if payload.mqtt_password else ""

        if not mqtt_host:
            mqtt_status = {"status": "error", "message": "Chưa điền MQTT Host"}
        else:
            mqtt_result = {"status": "error", "message": "MQTT Timeout: Hết thời gian kết nối"}
            event = threading.Event()
            
            def on_connect_test(client, userdata, flags, rc, *args, **kwargs):
                code = getattr(rc, "value", rc)
                if code == 0:
                    mqtt_result["status"] = "success"
                    mqtt_result["message"] = "Kết nối MQTT Broker thành công!"
                else:
                    mqtt_result["status"] = "error"
                    mqtt_result["message"] = f"Broker từ chối kết nối (Mã lỗi {code})"
                event.set()
                
            client_id = f"test_mqtt_{int(time.time())}"
            try:
                try:
                    client = mqtt.Client(mqtt.CallbackAPIVersion.VERSION1, client_id=client_id)
                except Exception:
                    client = mqtt.Client(client_id=client_id)
                    
                if mqtt_user:
                    client.username_pw_set(mqtt_user, mqtt_pass if mqtt_pass else None)
                    
                client.on_connect = on_connect_test
                client.connect_async(mqtt_host, mqtt_port, keepalive=10)
                client.loop_start()
                
                event.wait(timeout=3.5)
                client.loop_stop()
                client.disconnect()
                mqtt_status = mqtt_result
            except Exception as e:
                mqtt_status = {"status": "error", "message": f"Lỗi kết nối MQTT: {str(e)}"}

        # 4. Test Telegram
        telegram_status = {"status": "success", "message": "Cấu hình Telegram trống (bỏ qua)"}
        telegram_token = payload.telegram_bot_token.strip() if payload.telegram_bot_token else ""
        telegram_chat = payload.telegram_chat_id.strip() if payload.telegram_chat_id else ""
        
        if telegram_token or telegram_chat:
            if not telegram_token or not telegram_chat:
                telegram_status = {"status": "error", "message": "Thiếu Bot Token hoặc Chat ID"}
            else:
                try:
                    url_tg = f"https://api.telegram.org/bot{telegram_token}/sendMessage"
                    test_message = "🔔 AI Vision: Chẩn đoán kết nối thử nghiệm thành công!"
                    data_tg = {"chat_id": telegram_chat, "text": test_message}
                    r_tg = requests.post(url_tg, json=data_tg, timeout=8)
                    if r_tg.status_code == 200:
                        telegram_status = {"status": "success", "message": "Kết nối Telegram thành công (Đã gửi tin nhắn!)"}
                    else:
                        telegram_status = {"status": "error", "message": f"Telegram báo lỗi {r_tg.status_code}: {r_tg.text[:150]}"}
                except Exception as e:
                    telegram_status = {"status": "error", "message": f"Lỗi Telegram: {str(e)}"}

        return {
            "ha": ha_status,
            "ai": ai_status,
            "mqtt": mqtt_status,
            "telegram": telegram_status
        }

    @app.post("/api/test_ha")
    async def test_ha_connection(payload: dict):
        ha_url = payload.get("ha_url", "").strip()
        ha_token = payload.get("ha_token", "").strip()
        
        if not ha_url:
            return JSONResponse(status_code=400, content={"status": "error", "message": "Home Assistant URL không được để trống"})
            
        if not ha_token:
            # Fallback to env token
            ha_token = os.getenv("SUPERVISOR_TOKEN", "")
            
        headers = {}
        if ha_token:
            headers["Authorization"] = f"Bearer {ha_token}"
            
        try:
            url = f"{ha_url.rstrip('/')}/api/"
            print(f"[API] Testing HA connection to: {url}")
            r = requests.get(url, headers=headers, timeout=10)
            
            if r.status_code == 200:
                try:
                    msg = r.json().get("message", "API running.")
                except Exception:
                    msg = "API running."
                return {"status": "success", "message": f"Kết nối thành công! HA phản hồi: {msg}"}
            elif r.status_code == 401:
                return JSONResponse(status_code=401, content={"status": "error", "message": "Lỗi 401 Unauthorized: Token không chính xác"})
            elif r.status_code == 403:
                return JSONResponse(status_code=403, content={"status": "error", "message": "Lỗi 403 Forbidden: Truy cập bị chặn"})
            else:
                return JSONResponse(status_code=r.status_code, content={"status": "error", "message": f"Mã lỗi từ HA: {r.status_code}"})
                
        except requests.exceptions.Timeout:
            return JSONResponse(status_code=504, content={"status": "error", "message": "Hết thời gian chờ kết nối (Timeout). Hãy kiểm tra lại URL."})
        except requests.exceptions.ConnectionError:
            return JSONResponse(status_code=502, content={"status": "error", "message": "Không thể kết nối tới HA. Kiểm tra địa chỉ/Port hoặc tường lửa."})
        except Exception as e:
            return JSONResponse(status_code=500, content={"status": "error", "message": f"Lỗi không xác định: {str(e)}"})

    @app.post("/api/test_telegram")
    async def test_telegram_connection(payload: dict):
        bot_token = payload.get("telegram_bot_token", "").strip()
        chat_id = payload.get("telegram_chat_id", "").strip()
        
        if not bot_token or not chat_id:
            return JSONResponse(status_code=400, content={"status": "error", "message": "Bot Token và Chat ID không được để trống"})
            
        try:
            url = f"https://api.telegram.org/bot{bot_token}/sendMessage"
            test_message = "🔔 AI Vision: Kiểm tra kết nối Telegram Bot thành công!"
            data = {"chat_id": chat_id, "text": test_message}
            r = requests.post(url, json=data, timeout=10)
            
            if r.status_code == 200:
                return {"status": "success", "message": "Gửi tin nhắn thử nghiệm tới Telegram thành công!"}
            else:
                return JSONResponse(status_code=r.status_code, content={"status": "error", "message": f"Telegram API trả về mã lỗi {r.status_code}: {r.text[:200]}"})
        except Exception as e:
            return JSONResponse(status_code=500, content={"status": "error", "message": f"Không thể kết nối Telegram API: {str(e)}"})

    @app.get("/api/camera_entities")
    async def get_camera_entities(ha_url: Optional[str] = None, ha_token: Optional[str] = None):
        # Resolve target URL and token
        url = ha_url.strip() if ha_url else config.ha_url
        token = ha_token.strip() if ha_token else config.ha_token
        
        if not token:
            token = os.getenv("SUPERVISOR_TOKEN", "")
            
        if not url:
            return []
            
        headers = {}
        if token:
            headers["Authorization"] = f"Bearer {token}"
            
        try:
            target_url = f"{url.rstrip('/')}/api/states"
            r = requests.get(target_url, headers=headers, timeout=10)
            if r.status_code == 200:
                entities = r.json()
                filtered = []
                for ent in entities:
                    ent_id = ent.get("entity_id", "")
                    has_picture = ent.get("attributes", {}).get("entity_picture") is not None
                    if ent_id.startswith("camera.") or has_picture:
                        filtered.append({
                            "entity_id": ent_id,
                            "friendly_name": ent.get("attributes", {}).get("friendly_name", ent_id),
                            "type": "camera" if ent_id.startswith("camera.") else "entity_picture"
                        })
                # Sort by friendly name
                filtered.sort(key=lambda x: x["friendly_name"].lower())
                return filtered
            else:
                print(f"[API] HA States API returned status {r.status_code}")
                return []
        except Exception as e:
            print(f"[API] Error querying HA entities: {e}")
            return []

    # Ensure images folder exists
    os.makedirs(images_dir, exist_ok=True)
    
    # Mount static folder for saved images
    app.mount("/images", StaticFiles(directory=images_dir), name="images")

    # Mount static dashboard frontend
    app.mount("/", StaticFiles(directory="static", html=True), name="static")

    return app
