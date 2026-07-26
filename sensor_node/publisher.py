# publisher.py - MQTT Publisher for Power Station Telemetry
import time
import json
import random
import paho.mqtt.client as mqtt

import sys
import os
# Add script directory to sys.path to resolve local imports cleanly
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

# Import configuration and sensor generator
import config
from sensors import generate_sensor_data

def on_connect(client, userdata, flags, rc):
    """Callback function when publisher successfully connects to the broker."""
    if rc == 0:
        print("Successfully connected to MQTT Broker!")
    else:
        print(f"Connection failed with code {rc}")

def run_publisher():
    """Main loop to publish sensor readings to the MQTT topic."""
    # Initialize Paho MQTT client
    client = mqtt.Client("PowerStationPublisher")
    client.on_connect = on_connect

    print(f"Connecting to broker at {config.MQTT_BROKER}:{config.MQTT_PORT}...")
    try:
        client.connect(config.MQTT_BROKER, config.MQTT_PORT, 60)
    except Exception as e:
        print(f"Could not connect to MQTT broker: {e}")
        print("Please make sure Mosquitto broker is running.")
        return

    # Start loop in a background thread to maintain connections
    client.loop_start()

    print(f"Starting simulation. Publishing to topic: '{config.MQTT_TOPIC}' every {config.PUBLISH_INTERVAL}s.")
    print("Press Ctrl+C to stop.\n")

    try:
        while True:
            # For each station in our network, generate and publish telemetry data
            for station_id in config.STATION_IDS:
                # Randomly decide whether to inject a fault based on FAULT_PROBABILITY
                inject_fault = random.random() < config.FAULT_PROBABILITY
                
                # Generate mock data
                telemetry = generate_sensor_data(station_id, inject_fault)
                
                # Convert dictionary to JSON string
                payload = json.dumps(telemetry)
                
                # Publish the reading
                client.publish(config.MQTT_TOPIC, payload)
                
                status_msg = " [FAULT INJECTED]" if inject_fault else ""
                print(f"Published telemetry for {station_id} -> V: {telemetry['voltage']}V | I: {telemetry['current']}A | Freq: {telemetry['frequency']}Hz | Temp: {telemetry['temperature']}°C | Load: {telemetry['load']}%{status_msg}")
            
            # Wait for the next interval
            time.sleep(config.PUBLISH_INTERVAL)
            print("-" * 50)
            
    except KeyboardInterrupt:
        print("\nStopping simulated telemetry publisher...")
    finally:
        # Clean shutdown of MQTT client
        client.loop_stop()
        client.disconnect()
        print("Publisher disconnected. Goodbye.")

if __name__ == "__main__":
    run_publisher()
