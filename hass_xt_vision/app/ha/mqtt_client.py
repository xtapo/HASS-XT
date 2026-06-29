import os
import json
import time
import cv2
import paho.mqtt.client as mqtt
from typing import Dict, Any, List

class HAMQTTClient:
    def __init__(self, host: str, port: int, user: str = "", password: str = "", device_name: str = "hass_xt_camera"):
        self.host = host.strip() if host else "core-mosquitto"
        self.port = port
        self.user = user.strip() if user else ""
        self.password = password.strip() if password else ""
        self.device_name = device_name
        self.connected = False
        self.client = None

    def start(self):
        self.stop()
        try:
            print(f"[MQTT] Connecting to broker {self.host}:{self.port} (user: {self.user})...")
            # Support both paho-mqtt v1.x and v2.x callback API versions with fresh client instance
            client_id = f"hass_xt_{int(time.time())}"
            try:
                self.client = mqtt.Client(mqtt.CallbackAPIVersion.VERSION1, client_id=client_id)
            except AttributeError:
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

    def _on_connect(self, client, userdata, flags, rc, properties=None):
        code = getattr(rc, "value", rc)
        if code == 0:
            print(f"[MQTT] Successfully connected to MQTT broker at {self.host}!")
            self.connected = True
            self._publish_discovery_configs()
        else:
            print(f"[MQTT] Connection failed to {self.host} with code {code}")
            self.connected = False
            # Fallback to internal HA broker if running as HA Add-on and external IP failed
            if self.host != "core-mosquitto" and (os.path.exists("/data/options.json") or os.path.exists("/data")):
                print("[MQTT] Attempting fallback to internal HA broker 'core-mosquitto'...")
                self.host = "core-mosquitto"
                self.start()

    def _on_disconnect(self, client, userdata, rc, properties=None):
        print(f"[MQTT] Disconnected from MQTT broker (rc: {rc}).")
        self.connected = False

    def _publish_discovery_configs(self):
        if not self.client or not self.connected:
            return

        device_info = {
            "identifiers": [self.device_name],
            "name": "HASS-XT AI Camera",
            "model": "AI Vision Engine v1.0",
            "manufacturer": "HASS-XT"
        }

        # 1. Motion Binary Sensor Discovery
        motion_config = {
            "name": "AI Camera Motion",
            "unique_id": f"{self.device_name}_motion",
            "state_topic": f"hass_xt/{self.device_name}/motion/state",
            "device_class": "motion",
            "payload_on": "ON",
            "payload_off": "OFF",
            "device": device_info
        }
        self.client.publish(f"homeassistant/binary_sensor/{self.device_name}/motion/config", json.dumps(motion_config), retain=True)

        # 2. Person Detected Binary Sensor Discovery
        person_config = {
            "name": "AI Camera Person Detected",
            "unique_id": f"{self.device_name}_person",
            "state_topic": f"hass_xt/{self.device_name}/person/state",
            "device_class": "occupancy",
            "payload_on": "ON",
            "payload_off": "OFF",
            "device": device_info
        }
        self.client.publish(f"homeassistant/binary_sensor/{self.device_name}/person/config", json.dumps(person_config), retain=True)

        # 3. Detected Objects Counter Sensor Discovery
        count_config = {
            "name": "AI Camera Object Count",
            "unique_id": f"{self.device_name}_count",
            "state_topic": f"hass_xt/{self.device_name}/count/state",
            "unit_of_measurement": "objects",
            "icon": "mdi:eye-outline",
            "device": device_info
        }
        self.client.publish(f"homeassistant/sensor/{self.device_name}/count/config", json.dumps(count_config), retain=True)

        # 4. Camera Entity Discovery (Image/Snapshot)
        camera_config = {
            "name": "AI Camera Snapshot",
            "unique_id": f"{self.device_name}_snapshot",
            "topic": f"hass_xt/{self.device_name}/snapshot",
            "device": device_info
        }
        self.client.publish(f"homeassistant/camera/{self.device_name}/snapshot/config", json.dumps(camera_config), retain=True)

        print("[MQTT] Home Assistant Discovery configurations published.")

    def update_states(self, motion_detected: bool, detections: List[Dict[str, Any]], frame=None):
        if not self.connected or not self.client:
            return

        motion_payload = "ON" if motion_detected else "OFF"
        self.client.publish(f"hass_xt/{self.device_name}/motion/state", motion_payload)

        person_detected = any(d["class"] == "person" for d in detections)
        person_payload = "ON" if person_detected else "OFF"
        self.client.publish(f"hass_xt/{self.device_name}/person/state", person_payload)

        self.client.publish(f"hass_xt/{self.device_name}/count/state", str(len(detections)))

        # Publish frame snapshot if motion or person detected
        if (motion_detected or person_detected) and frame is not None:
            ret, jpeg = cv2.imencode('.jpg', frame, [int(cv2.IMWRITE_JPEG_QUALITY), 75])
            if ret:
                self.client.publish(f"hass_xt/{self.device_name}/snapshot", jpeg.tobytes())

    def stop(self):
        self.connected = False
        if self.client:
            try:
                self.client.loop_stop()
                self.client.disconnect()
            except Exception:
                pass
