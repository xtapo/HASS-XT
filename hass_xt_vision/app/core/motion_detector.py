import cv2
import numpy as np
from typing import Tuple, List

class MotionDetector:
    def __init__(self, sensitivity: int = 25, min_area: int = 500):
        self.sensitivity = sensitivity
        self.min_area = min_area
        self.bg_subtractor = cv2.createBackgroundSubtractorMOG2(history=500, varThreshold=sensitivity, detectShadows=False)

    def detect(self, frame: np.ndarray) -> Tuple[bool, List[Tuple[int, int, int, int]]]:
        if frame is None:
            return False, []

        # Convert to grayscale and blur to reduce noise
        gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
        blur = cv2.GaussianBlur(gray, (21, 21), 0)

        # Apply background subtraction
        fg_mask = self.bg_subtractor.apply(blur)
        
        # Threshold and dilate mask
        _, thresh = cv2.threshold(fg_mask, 200, 255, cv2.THRESH_BINARY)
        dilated = cv2.dilate(thresh, None, iterations=2)

        # Find contours of moving areas
        contours, _ = cv2.findContours(dilated, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        
        motion_boxes = []
        motion_detected = False

        for contour in contours:
            if cv2.contourArea(contour) < self.min_area:
                continue
            motion_detected = True
            (x, y, w, h) = cv2.boundingRect(contour)
            motion_boxes.append((x, y, w, h))

        return motion_detected, motion_boxes
