import json
import time
import cv2
import paho.mqtt.client as mqtt
from typing import Dict, Any, List

class HAMQTTClient:
    def __init__(self, host: str, port: int, user: str = "", password: str = "", device_name: str = "hass_xt_camera"):
        self.host = host
        self.port = port
        self.user = user
        self.password = password
        self.device_name = device_name
        self.client = mqtt.Client(client_id=f"hass_xt_{int(time.time())}")
        self.connected = False
        
        if self.user and self.password:
            self.client.username_pw_set(self.user, self.password)

        self.client.on_connect = self._on_connect
        self.client.on_disconnect = self._on_disconnect

    def start(self):
        try:
            print(f"[MQTT] Connecting to broker {self.host}:{self.port}...")
            self.client.connect_async(self.host, self.port, keepalive=60)
            self.client.loop_start()
        except Exception as e:
            print(f"[MQTT] Connection error: {e}")

    def _on_connect(self, client, userdata, flags, rc):
        if rc == 0:
            print("[MQTT] Successfully connected to MQTT broker!")
            self.connected = True
            self._publish_discovery_configs()
        else:
            print(f"[MQTT] Connection failed with code {rc}")

    def _on_disconnect(self, client, userdata, rc):
        print("[MQTT] Disconnected from MQTT broker.")
        self.connected = False

    def _publish_discovery_configs(self):
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
        if not self.connected:
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
        self.client.loop_stop()
        self.client.disconnect()
