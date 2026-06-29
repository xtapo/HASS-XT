import os
import cv2
import time
import threading
import numpy as np

# Force FFMPEG TCP transport for RTSP streams (prevents UDP packet drops and connection failures)
os.environ["OPENCV_FFMPEG_CAPTURE_OPTIONS"] = "rtsp_transport;tcp;stimeout;5000000"

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
        print(f"[StreamReader] Connecting to RTSP stream: {self.rtsp_url}")
        if self.cap is not None:
            try:
                self.cap.release()
            except Exception:
                pass

        # Open capture with FFMPEG backend
        self.cap = cv2.VideoCapture(self.rtsp_url, cv2.CAP_FFMPEG)
        if not self.cap.isOpened():
            print(f"[StreamReader] WARNING: Could not connect to real RTSP camera at '{self.rtsp_url}'. Using test simulation generator.")
            self.is_synthetic = True
        else:
            print(f"[StreamReader] SUCCESS: Connected to real RTSP camera stream!")
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
        cv2.putText(img, "SIMULATED TEST STREAM", (x1, y1 - 10), cv2.FONT_HERSHEY_SIMPLEX, 0.4, (255, 255, 255), 1)

        # Draw header overlay
        cv2.putText(img, f"HASS-XT Test Mode (Check RTSP URL) - {time.strftime('%H:%M:%S')}", (20, 30),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 220, 255), 1)
        return img

    def _update(self):
        frame_count = 0
        last_retry = time.time()
        self._connect()

        while self.running:
            now = time.time()
            if self.is_synthetic:
                frame_count += 1
                frame = self._generate_synthetic_frame(frame_count)
                time.sleep(0.04) # ~25 FPS

                # Periodically retry connecting to real camera every 10s
                if now - last_retry > 10.0:
                    last_retry = now
                    self._connect()
            else:
                ret, frame = self.cap.read()
                if not ret or frame is None:
                    print("[StreamReader] Frame read failed. Reconnecting in 3 seconds...")
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
