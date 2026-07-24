# config.py - Configuration settings for the Fog Node

# MQTT Broker configuration
MQTT_BROKER = "localhost"
MQTT_PORT = 1883
MQTT_TOPIC = "power/grid/data"

# Local Edge Storage (for local alerts and edge resiliency)
# We will use a local SQLite database file to log alerts at the edge.
import os
LOCAL_DB_PATH = os.path.abspath(os.path.join(os.path.dirname(__file__), "fog_alerts.db"))

# Fog Node Flask API Configuration
FOG_HOST = "0.0.0.0"
FOG_PORT = 5001

# Cloud Communication Settings
# When AWS_MOCK_MODE is True, the Fog Node will write processed telemetry
# and faults to a local database that the dashboard can read directly,
# simulating the cloud without requiring active AWS credentials.
AWS_MOCK_MODE = True

# Production AWS Settings (active when AWS_MOCK_MODE = False)
AWS_API_GATEWAY_URL = "https://your-api-gateway-id.execute-api.us-east-1.amazonaws.com/prod/telemetry"
AWS_REGION = "us-east-1"

# Rule Engine Thresholds
RULES = {
    "voltage": {
        "low_threshold": 210.0,
        "high_threshold": 250.0
    },
    "current": {
        "max_threshold": 400.0
    },
    "frequency": {
        "low_threshold": 49.0,
        "high_threshold": 51.0
    },
    "temperature": {
        "max_threshold": 90.0
    },
    "load": {
        "max_threshold": 95.0
    }
}
