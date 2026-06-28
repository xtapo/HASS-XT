import cv2
import time
import asyncio
from fastapi import FastAPI, Response
from fastapi.responses import StreamingResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel
from app.config import config

class ConfigUpdateModel(BaseModel):
    motion_sensitivity: int
    ai_confidence: float

def create_app(stream_reader, motion_detector, ai_engine, mqtt_client) -> FastAPI:
    app = FastAPI(title="HASS-XT AI Vision Web API", version="1.0.0")
    
    # Store dynamic state
    app.state.latest_annotated_frame = None
    app.state.latest_detections = []
    app.state.motion_detected = False
    app.state.fps = 0.0

    @app.get("/api/status")
    async def get_status():
        return {
            "status": "online",
            "device_name": config.device_name,
            "motion_detected": app.state.motion_detected,
            "detections_count": len(app.state.latest_detections),
            "detections": app.state.latest_detections,
            "mqtt_connected": mqtt_client.connected,
            "fps": round(app.state.fps, 1)
        }

    @app.get("/api/config")
    async def get_config():
        return {
            "rtsp_url": config.rtsp_url,
            "motion_sensitivity": motion_detector.sensitivity,
            "ai_confidence": ai_engine.confidence_threshold
        }

    @app.post("/api/config")
    async def update_config(payload: ConfigUpdateModel):
        motion_detector.sensitivity = payload.motion_sensitivity
        ai_engine.confidence_threshold = payload.ai_confidence
        return {"status": "success", "message": "Configuration updated successfully"}

    def generate_mjpeg():
        while True:
            frame = app.state.latest_annotated_frame
            if frame is not None:
                ret, jpeg = cv2.imencode('.jpg', frame, [int(cv2.IMWRITE_JPEG_QUALITY), 80])
                if ret:
                    yield (b'--frame\r\n'
                           b'Content-Type: image/jpeg\r\n\r\n' + jpeg.tobytes() + b'\r\n')
            time.sleep(0.04) # ~25 FPS

    @app.get("/api/stream")
    async def video_stream():
        return StreamingResponse(generate_mjpeg(), media_type='multipart/x-mixed-replace; boundary=frame')

    # Mount static files for dashboard frontend
    app.mount("/", StaticFiles(directory="static", html=True), name="static")

    return app
