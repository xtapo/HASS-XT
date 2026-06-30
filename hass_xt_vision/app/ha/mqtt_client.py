import os
import json
import time
import paho.mqtt.client as mqtt
from typing import Dict, Any, List

class HAMQTTClient:
    def __init__(self, host: str, port: int, user: str = "", password: str = "", prefix: str = "ai_vision"):
        self.host = host.strip() if host else "core-mosquitto"
        self.port = port
        self.user = user.strip() if user else ""
        self.password = password.strip() if password else ""
        self.prefix = prefix.strip() if prefix else "ai_vision"
        self.connected = False
        self.status_text = "Disconnected"
        self.client = None

    def start(self):
        self.stop()
        try:
            self.status_text = "Connecting..."
            print(f"[MQTT] Connecting to broker {self.host}:{self.port} (user: '{self.user}')...")
            client_id = f"hass_xt_describer_{int(time.time())}"
            
            try:
                self.client = mqtt.Client(mqtt.CallbackAPIVersion.VERSION1, client_id=client_id)
            except Exception:
                self.client = mqtt.Client(client_id=client_id)

            if self.user:
                self.client.username_pw_set(self.user, self.password if self.password else None)

            self.client.on_connect = self._on_connect
            self.client.on_disconnect = self._on_disconnect

            self.client.connect_async(self.host, self.port, keepalive=60)
            self.client.loop_start()
        except Exception as e:
            print(f"[MQTT] Connection setup error: {e}")
            self.connected = False
            self.status_text = f"Error: {e}"

    def _on_connect(self, client, userdata, flags, rc, *args, **kwargs):
        code = getattr(rc, "value", rc)
        print(f"[MQTT] Connection callback response code: {code}")
        if code == 0:
            print(f"[MQTT] Successfully connected to MQTT broker at {self.host}!")
            self.connected = True
            self.status_text = "Connected"
            try:
                self.publish_discovery_for_all()
            except Exception as e:
                print(f"[MQTT] Error publishing discovery configs: {e}")
        else:
            self.connected = False
            if code == 4:
                self.status_text = "Bad Username/Password (Code 4)"
            elif code == 5:
                self.status_text = "Not Authorized (Code 5)"
            else:
                self.status_text = f"Refused (Code {code})"
            print(f"[MQTT] Connection rejected by {self.host}: {self.status_text}")
            
            # Fallback to internal HA broker if running as HA Add-on
            if self.host != "core-mosquitto" and (os.path.exists("/data") or os.path.exists("/data/describer_config.json")):
                print("[MQTT] Triggering automatic fallback to internal HA broker 'core-mosquitto'...")
                self.host = "core-mosquitto"
                self.start()

    def _on_disconnect(self, client, userdata, rc, *args, **kwargs):
        code = getattr(rc, "value", rc)
        print(f"[MQTT] Disconnected from MQTT broker (code: {code}).")
        self.connected = False
        if code != 0 and self.status_text == "Connected":
            self.status_text = "Disconnected"

    def _get_slug(self, entity_id: str) -> str:
        return entity_id.replace(".", "_")

    def publish_sensor_discovery(self, entity_id: str):
        if not self.client or not self.connected:
            return

        entity_slug = self._get_slug(entity_id)
        # Clean title for entity (e.g. Front Door if entity_id is camera.front_door)
        clean_name = entity_id.split(".")[-1].replace("_", " ").title()
        
        discovery_topic = f"homeassistant/sensor/{self.prefix}_{entity_slug}/config"
        
        discovery_payload = {
            "name": f"{self.prefix.upper()} {clean_name}",
            "unique_id": f"{self.prefix}_{entity_slug}",
            "state_topic": f"{self.prefix}/{entity_slug}/state",
            "json_attributes_topic": f"{self.prefix}/{entity_slug}/attributes",
            "icon": "mdi:comment-eye-outline",
            "value_template": "{{ value }}",
            "device": {
                "identifiers": [f"{self.prefix}_describer_device"],
                "name": "AI Vision Entity Describer",
                "model": "AI Vision Describer v2.0",
                "manufacturer": "HASS-XT"
            }
        }
        
        print(f"[MQTT] Publishing discovery config to {discovery_topic}")
        self.client.publish(discovery_topic, json.dumps(discovery_payload), retain=True)

    def publish_discovery_for_all(self):
        from app.config import config
        for entity_id in config.camera_entities:
            self.publish_sensor_discovery(entity_id)

    def update_sensor_state(self, entity_id: str, description: str, timestamp: str, status: str, error_message: str = ""):
        if not self.client or not self.connected:
            print("[MQTT] Cannot publish state. MQTT client not connected.")
            return

        # Ensure discovery config is sent first
        self.publish_sensor_discovery(entity_id)

        entity_slug = self._get_slug(entity_id)
        
        # State: Truncate to 250 characters to avoid Home Assistant state limit of 255 chars
        state_payload = description[:250] if description else "Unknown/No description"
        if description and len(description) > 250:
            state_payload = description[:247] + "..."

        if status == "error":
            state_payload = f"Error: {error_message}"[:250]

        state_topic = f"{self.prefix}/{entity_slug}/state"
        attributes_topic = f"{self.prefix}/{entity_slug}/attributes"

        # Attributes: full description + metadata
        attributes_payload = {
            "full_description": description if description else "",
            "timestamp": timestamp,
            "entity_id": entity_id,
            "status": status,
            "error_message": error_message
        }

        print(f"[MQTT] Publishing state to {state_topic}")
        self.client.publish(state_topic, state_payload, retain=True)
        print(f"[MQTT] Publishing attributes to {attributes_topic}")
        self.client.publish(attributes_topic, json.dumps(attributes_payload), retain=True)

    def stop(self):
        self.connected = False
        if self.client:
            try:
                self.client.loop_stop()
                self.client.disconnect()
            except Exception:
                pass
            self.client = None
