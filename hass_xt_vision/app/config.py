import os
import json
from pydantic import BaseModel

class AppConfig(BaseModel):
    rtsp_url: str = "rtsp://wowzaec2demo.streamlock.net/vod/mp4:BigBuckBunny.mp4"
    mqtt_host: str = "localhost"
    mqtt_port: int = 1883
    mqtt_user: str = ""
    mqtt_password: str = ""
    motion_sensitivity: int = 25
    ai_confidence: float = 0.5
    device_name: str = "hass_xt_camera"

def get_options_file_path() -> str:
    ha_options_file = "/data/options.json"
    if os.path.exists(ha_options_file) or os.path.exists("/data"):
        return ha_options_file
    return "local_options.json"

def load_config() -> AppConfig:
    filepath = get_options_file_path()
    if os.path.exists(filepath):
        try:
            with open(filepath, "r", encoding="utf-8") as f:
                data = json.load(f)
                return AppConfig(**data)
        except Exception as e:
            print(f"[Config] Error loading options from {filepath}: {e}")
    
    # Fallback to environment variables or defaults
    return AppConfig(
        rtsp_url=os.getenv("RTSP_URL", "rtsp://wowzaec2demo.streamlock.net/vod/mp4:BigBuckBunny.mp4"),
        mqtt_host=os.getenv("MQTT_HOST", "localhost"),
        mqtt_port=int(os.getenv("MQTT_PORT", "1883")),
        mqtt_user=os.getenv("MQTT_USER", ""),
        mqtt_password=os.getenv("MQTT_PASSWORD", ""),
        motion_sensitivity=int(os.getenv("MOTION_SENSITIVITY", "25")),
        ai_confidence=float(os.getenv("AI_CONFIDENCE", "0.5")),
        device_name=os.getenv("DEVICE_NAME", "hass_xt_camera")
    )

def save_config(new_data: dict):
    global config
    for key, value in new_data.items():
        if hasattr(config, key):
            setattr(config, key, value)
    
    filepath = get_options_file_path()
    try:
        with open(filepath, "w", encoding="utf-8") as f:
            json.dump(config.model_dump(), f, indent=2, ensure_ascii=False)
        print(f"[Config] Saved updated options to {filepath}")
    except Exception as e:
        print(f"[Config] Error saving config to {filepath}: {e}")

config = load_config()
