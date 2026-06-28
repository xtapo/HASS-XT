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

def load_config() -> AppConfig:
    # Check if running inside Home Assistant Add-on container (/data/options.json)
    ha_options_file = "/data/options.json"
    if os.path.exists(ha_options_file):
        try:
            with open(ha_options_file, "r") as f:
                data = json.load(f)
                return AppConfig(**data)
        except Exception as e:
            print(f"[Config] Error loading HA options.json: {e}")
    
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

config = load_config()
