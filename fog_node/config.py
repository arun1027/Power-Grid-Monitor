# config.py - Configuration settings for the Fog Node

# MQTT Broker configuration (Local Mosquitto)
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

# AWS IoT Core Configuration
AWS_IOT_ENDPOINT = "aojrwb4mjzc6m-ats.iot.us-east-1.amazonaws.com"
AWS_IOT_TOPIC = "powergrid/data"
AWS_REGION = "us-east-1"

# Certificate Paths
ROOT_CA_PATH = os.path.abspath(os.path.join(os.path.dirname(__file__), "certs", "AmazonRootCA1.pem"))
DEVICE_CERT_PATH = os.path.abspath(os.path.join(os.path.dirname(__file__), "certs", "device.pem.crt"))
PRIVATE_KEY_PATH = os.path.abspath(os.path.join(os.path.dirname(__file__), "certs", "private.pem.key"))

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
