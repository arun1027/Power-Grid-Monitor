# config.py - Configuration settings for the Sensor Simulator Node

# MQTT Broker configuration
MQTT_BROKER = "localhost"
MQTT_PORT = 1883
MQTT_TOPIC = "power/grid/data"
PUBLISH_INTERVAL = 5  # seconds between sensor readings

# List of simulated Power Stations
STATION_IDS = ["PS001", "PS002", "PS003", "PS004", "PS005"]

# Sensor Normal Ranges
SENSOR_RANGES = {
    "voltage": {"min": 220, "max": 240},
    "current": {"min": 250, "max": 350},
    "frequency": {"min": 49.5, "max": 50.5},
    "temperature": {"min": 40, "max": 70},
    "load": {"min": 40, "max": 90}
}

# Fault simulation settings
# Chance of generating an anomalous value on any sensor read (e.g., 0.1 means 10%)
FAULT_PROBABILITY = 0.15
