import time
import threading
import uvicorn
from app.config import config
from app.core.stream_reader import StreamReader
from app.core.motion_detector import MotionDetector
from app.core.ai_engine import AIEngine
from app.ha.mqtt_client import HAMQTTClient
from app.web.server import create_app

def processing_loop(stream_reader, motion_detector, ai_engine, mqtt_client, app):
    print("[ProcessingLoop] Starting AI vision processing pipeline...")
    last_time = time.time()
    frame_count = 0

    while True:
        frame = stream_reader.get_frame()
        if frame is None:
            time.sleep(0.01)
            continue

        # 1. Motion Detection
        motion_detected, motion_boxes = motion_detector.detect(frame)
        
        # 2. AI Inference (Run when motion detected or periodically)
        annotated_frame, detections = ai_engine.analyze_frame(frame, motion_boxes)

        # 3. Calculate FPS
        frame_count += 1
        now = time.time()
        if now - last_time >= 1.0:
            app.state.fps = frame_count / (now - last_time)
            frame_count = 0
            last_time = now

        # 4. Update Web App State
        app.state.latest_annotated_frame = annotated_frame
        app.state.latest_detections = detections
        app.state.motion_detected = motion_detected

        # 5. Send states and snapshots to Home Assistant via MQTT
        mqtt_client.update_states(motion_detected, detections, annotated_frame)

        time.sleep(0.02) # ~50 Hz loop

def main():
    print("=" * 60)
    print("      HASS-XT AI Vision Camera Engine for Home Assistant      ")
    print("=" * 60)

    stream_reader = StreamReader(rtsp_url=config.rtsp_url)
    motion_detector = MotionDetector(sensitivity=config.motion_sensitivity)
    ai_engine = AIEngine(confidence_threshold=config.ai_confidence)
    mqtt_client = HAMQTTClient(
        host=config.mqtt_host,
        port=config.mqtt_port,
        user=config.mqtt_user,
        password=config.mqtt_password,
        device_name=config.device_name
    )

    # Start services
    stream_reader.start()
    mqtt_client.start()

    # Create FastAPI App
    app = create_app(stream_reader, motion_detector, ai_engine, mqtt_client)

    # Start background processing thread
    proc_thread = threading.Thread(
        target=processing_loop,
        args=(stream_reader, motion_detector, ai_engine, mqtt_client, app),
        daemon=True
    )
    proc_thread.start()

    # Run Uvicorn web server
    uvicorn.run(app, host="0.0.0.0", port=8000, log_level="info")

if __name__ == "__main__":
    main()
