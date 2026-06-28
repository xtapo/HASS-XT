import cv2
import time
import threading
import numpy as np

class StreamReader:
    def __init__(self, rtsp_url: str):
        self.rtsp_url = rtsp_url
        self.cap = None
        self.running = False
        self.thread = None
        self.latest_frame = None
        self.lock = threading.Lock()
        self.is_synthetic = False

    def start(self):
        self.running = True
        self.thread = threading.Thread(target=self._update, daemon=True)
        self.thread.start()

    def _connect(self):
        print(f"[StreamReader] Connecting to video stream: {self.rtsp_url}")
        self.cap = cv2.VideoCapture(self.rtsp_url)
        if not self.cap.isOpened():
            print(f"[StreamReader] Failed to open RTSP stream. Using synthetic stream generator for testing.")
            self.is_synthetic = True
        else:
            self.is_synthetic = False

    def _generate_synthetic_frame(self, frame_count: int) -> np.ndarray:
        # Create a 640x480 test image with moving objects and timestamp
        img = np.zeros((480, 640, 3), dtype=np.uint8)
        # Background gradient
        for y in range(480):
            img[y, :, :] = [30 + y // 10, 30, 40]
        
        # Draw simulated moving person/vehicle
        t = frame_count * 0.05
        x1 = int(320 + 200 * np.sin(t))
        y1 = int(240 + 50 * np.cos(t * 0.5))
        cv2.rectangle(img, (x1, y1), (x1 + 60, y1 + 120), (0, 255, 120), -1)
        cv2.putText(img, "SIMULATED PERSON", (x1, y1 - 10), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (255, 255, 255), 1)

        # Draw header overlay
        cv2.putText(img, f"HASS-XT Live Stream - {time.strftime('%Y-%m-%d %H:%M:%S')}", (20, 30),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 220, 255), 2)
        return img

    def _update(self):
        frame_count = 0
        self._connect()
        while self.running:
            if self.is_synthetic:
                frame_count += 1
                frame = self._generate_synthetic_frame(frame_count)
                time.sleep(0.04) # ~25 FPS
            else:
                ret, frame = self.cap.read()
                if not ret:
                    print("[StreamReader] Frame read failed. Attempting reconnect in 3 seconds...")
                    time.sleep(3)
                    self._connect()
                    continue
            
            with self.lock:
                self.latest_frame = frame

    def get_frame(self):
        with self.lock:
            if self.latest_frame is not None:
                return self.latest_frame.copy()
            return None

    def stop(self):
        self.running = False
        if self.thread:
            self.thread.join(timeout=1.0)
        if self.cap and not self.is_synthetic:
            self.cap.release()
