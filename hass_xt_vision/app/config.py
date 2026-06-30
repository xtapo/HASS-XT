import os
import json
from pydantic import BaseModel
from typing import List, Dict, Optional

class CameraSetting(BaseModel):
    scan_interval: Optional[int] = None
    ai_prompt: Optional[str] = None
    ai_model: Optional[str] = None
    motion_threshold: Optional[float] = None

class AppConfig(BaseModel):
    ha_url: str = "http://supervisor/core"
    ha_token: str = ""
    camera_entities: List[str] = []
    camera_settings: Dict[str, CameraSetting] = {}
    scan_interval: int = 30
    motion_threshold: float = 2.0
    ai_proxy_base_url: str = ""
    ai_api_key: str = ""
    ai_model: str = ""
    mqtt_host: str = "core-mosquitto"
    mqtt_port: int = 1883
    mqtt_user: str = ""
    mqtt_password: str = ""
    mqtt_prefix: str = "ai_vision"
    ai_prompt: str = "Hãy mô tả chi tiết hình ảnh này bằng tiếng Việt."
    telegram_bot_token: str = ""
    telegram_chat_id: str = ""

def get_config_file_path() -> str:
    # If /data directory exists (HA addon standard persistence), save there
    if os.path.exists("/data") or os.path.isdir("/data"):
        return "/data/describer_config.json"
    return "describer_config.json"

def load_config() -> AppConfig:
    filepath = get_config_file_path()
    if os.path.exists(filepath):
        try:
            with open(filepath, "r", encoding="utf-8") as f:
                data = json.load(f)
                # Handle potential list conversion for legacy or string inputs
                if "camera_entities" in data and isinstance(data["camera_entities"], str):
                    data["camera_entities"] = [
                        x.strip() for x in data["camera_entities"].split("\n") if x.strip()
                    ]
                return AppConfig(**data)
        except Exception as e:
            print(f"[Config] Error loading configuration from {filepath}: {e}")
    
    # Fallback to environment variables or defaults
    # When running under Home Assistant, SUPERVISOR_TOKEN is injected automatically
    ha_token_env = os.getenv("SUPERVISOR_TOKEN", "")
    
    return AppConfig(
        ha_url=os.getenv("HA_URL", "http://supervisor/core"),
        ha_token=os.getenv("HA_TOKEN", ha_token_env),
        camera_entities=[],
        scan_interval=int(os.getenv("SCAN_INTERVAL", "30")),
        motion_threshold=float(os.getenv("MOTION_THRESHOLD", "2.0")),
        ai_proxy_base_url=os.getenv("AI_PROXY_BASE_URL", ""),
        ai_api_key=os.getenv("AI_API_KEY", ""),
        ai_model=os.getenv("AI_MODEL", ""),
        mqtt_host=os.getenv("MQTT_HOST", "core-mosquitto"),
        mqtt_port=int(os.getenv("MQTT_PORT", "1883")),
        mqtt_user=os.getenv("MQTT_USER", ""),
        mqtt_password=os.getenv("MQTT_PASSWORD", ""),
        mqtt_prefix=os.getenv("MQTT_PREFIX", "ai_vision"),
        ai_prompt=os.getenv("AI_PROMPT", "Hãy mô tả chi tiết hình ảnh này bằng tiếng Việt."),
        telegram_bot_token=os.getenv("TELEGRAM_BOT_TOKEN", ""),
        telegram_chat_id=os.getenv("TELEGRAM_CHAT_ID", "")
    )

def save_config(new_data: dict):
    global config
    
    # Process string representation of camera entities if sent as list-like string
    if "camera_entities" in new_data and isinstance(new_data["camera_entities"], str):
        new_data["camera_entities"] = [
            x.strip() for x in new_data["camera_entities"].split("\n") if x.strip()
        ]
        
    for key, value in new_data.items():
        if hasattr(config, key):
            if key == "camera_settings" and isinstance(value, dict):
                typed_settings = {}
                for k, v in value.items():
                    if isinstance(v, dict):
                        typed_settings[k] = CameraSetting(**v)
                    else:
                        typed_settings[k] = v
                setattr(config, key, typed_settings)
            else:
                setattr(config, key, value)
    
    filepath = get_config_file_path()
    try:
        # Ensure parent directories exist
        db_dir = os.path.dirname(filepath)
        if db_dir:
            os.makedirs(db_dir, exist_ok=True)
            
        with open(filepath, "w", encoding="utf-8") as f:
            json.dump(config.model_dump(), f, indent=2, ensure_ascii=False)
        print(f"[Config] Saved updated configuration to {filepath}")
    except Exception as e:
        print(f"[Config] Error saving config to {filepath}: {e}")

config = load_config()
