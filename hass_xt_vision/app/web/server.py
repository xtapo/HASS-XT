import cv2
import time
import asyncio
from fastapi import FastAPI, Response
from fastapi.responses import StreamingResponse, Response, JSONResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel
from app.config import config, save_config

APP_VERSION = "1.1.0"

class ConfigUpdateModel(BaseModel):
    rtsp_url: str
    mqtt_host: str
    mqtt_port: int = 1883
    mqtt_user: str = ""
    mqtt_password: str = ""
    motion_sensitivity: int = 25
    ai_confidence: float = 0.5

def create_app(stream_reader, motion_detector, ai_engine, mqtt_client) -> FastAPI:
    app = FastAPI(title="HASS-XT AI Vision Web API", version=APP_VERSION)
    
    # Store dynamic state
    app.state.latest_annotated_frame = None
    app.state.latest_detections = []
    app.state.motion_detected = False
    app.state.fps = 0.0

    @app.get("/api/status")
    async def get_status():
        return {
            "status": "online",
            "version": APP_VERSION,
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
            "mqtt_host": config.mqtt_host,
            "mqtt_port": config.mqtt_port,
            "mqtt_user": config.mqtt_user,
            "mqtt_password": config.mqtt_password,
            "motion_sensitivity": motion_detector.sensitivity,
            "ai_confidence": ai_engine.confidence_threshold
        }

    @app.post("/api/config")
    async def update_config(payload: ConfigUpdateModel):
        # Check if RTSP URL changed
        rtsp_changed = (payload.rtsp_url != config.rtsp_url)
        mqtt_changed = (payload.mqtt_host != config.mqtt_host or payload.mqtt_port != config.mqtt_port or
                        payload.mqtt_user != config.mqtt_user or payload.mqtt_password != config.mqtt_password)

        # Save to disk and memory
        save_config(payload.model_dump())

        # Apply to engines
        motion_detector.sensitivity = payload.motion_sensitivity
        ai_engine.confidence_threshold = payload.ai_confidence

        if rtsp_changed and stream_reader:
            stream_reader.rtsp_url = payload.rtsp_url
            stream_reader._connect()

        if mqtt_changed and mqtt_client:
            mqtt_client.stop()
            mqtt_client.host = payload.mqtt_host
            mqtt_client.port = payload.mqtt_port
            mqtt_client.user = payload.mqtt_user
            mqtt_client.password = payload.mqtt_password
            if mqtt_client.user and mqtt_client.password:
                mqtt_client.client.username_pw_set(mqtt_client.user, mqtt_client.password)
            mqtt_client.start()

        return {"status": "success", "message": "Configuration updated and re-applied successfully"}

    @app.get("/api/snapshot")
    async def get_snapshot():
        frame = app.state.latest_annotated_frame
        if frame is not None:
            ret, jpeg = cv2.imencode('.jpg', frame, [int(cv2.IMWRITE_JPEG_QUALITY), 80])
            if ret:
                return Response(content=jpeg.tobytes(), media_type="image/jpeg", headers={
                    "Cache-Control": "no-cache, no-store, must-revalidate",
                    "Pragma": "no-cache",
                    "Expires": "0"
                })
        return Response(status_code=404)

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
        return StreamingResponse(generate_mjpeg(), media_type='multipart/x-mixed-replace; boundary=frame', headers={
            "Cache-Control": "no-cache, no-store, must-revalidate",
            "Pragma": "no-cache",
            "Expires": "0"
        })

    # Mount static files for dashboard frontend
    app.mount("/", StaticFiles(directory="static", html=True), name="static")

    return app
