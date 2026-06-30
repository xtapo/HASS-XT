import uvicorn
from app.config import config
from app.ha.mqtt_client import HAMQTTClient
from app.core.scanner import VisionScanner
from app.web.server import create_app

def main():
    print("=" * 60)
    print("     HASS-XT AI Vision Entity Describer Addon for Home Assistant     ")
    print("=" * 60)

    # Initialize MQTT client
    mqtt_client = HAMQTTClient(
        host=config.mqtt_host,
        port=config.mqtt_port,
        user=config.mqtt_user,
        password=config.mqtt_password,
        prefix=config.mqtt_prefix
    )

    # Initialize vision scanner background service
    scanner = VisionScanner(mqtt_client=mqtt_client)

    # Start services
    mqtt_client.start()
    scanner.start()

    # Create FastAPI App
    app = create_app(scanner=scanner, mqtt_client=mqtt_client)

    try:
        # Run Uvicorn web server
        uvicorn.run(app, host="0.0.0.0", port=1237, log_level="info")
    finally:
        # Stop background threads clean
        scanner.stop()
        mqtt_client.stop()

if __name__ == "__main__":
    main()
