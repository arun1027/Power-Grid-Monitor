# subscriber.py - Fog Node MQTT Subscriber and Data Processor
import time
import json
import sqlite3
import paho.mqtt.client as mqtt

import sys
import os
# Add script directory to sys.path to resolve local imports cleanly
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

# Import local components
import config
from data_filter import process_and_filter
from fault_detector import detect_faults
from api_client import send_to_cloud

def init_local_db():
    """Initializes a local database on the Fog Node for local alerts persistence (edge storage)."""
    conn = sqlite3.connect(config.LOCAL_DB_PATH)
    cursor = conn.cursor()
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS LocalAlerts (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            station_id TEXT NOT NULL,
            faults TEXT NOT NULL,
            voltage REAL,
            current REAL,
            frequency REAL,
            temperature REAL,
            load REAL,
            timestamp TEXT NOT NULL
        )
    ''')
    conn.commit()
    conn.close()

def log_alert_locally(data, faults):
    """Stores the detected fault logs locally on the Fog Node's database."""
    try:
        conn = sqlite3.connect(config.LOCAL_DB_PATH)
        cursor = conn.cursor()
        
        faults_str = ", ".join(faults)
        cursor.execute('''
            INSERT INTO LocalAlerts (station_id, faults, voltage, current, frequency, temperature, load, timestamp)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        ''', (
            data["station_id"],
            faults_str,
            data["voltage"],
            data["current"],
            data["frequency"],
            data["temperature"],
            data["load"],
            data["timestamp"]
        ))
        conn.commit()
        conn.close()
        print(f"[FOG STORAGE] Alert logged locally for {data['station_id']}: {faults_str}")
    except Exception as e:
        print(f"[FOG STORAGE ERROR] Failed to log alert locally: {e}")

def on_connect(client, userdata, flags, rc):
    if rc == 0:
        print(f"Connected to Mosquitto MQTT Broker. Subscribing to topic: '{config.MQTT_TOPIC}'...")
        result, mid = client.subscribe(config.MQTT_TOPIC)
        print(f"[DEBUG] Subscribe result={result}, mid={mid}")
    else:
        print(f"Connection to MQTT Broker failed with code {rc}")

def on_disconnect(client, userdata, rc):
    """Callback when the subscriber disconnects from the MQTT broker."""
    print(f"Disconnected from MQTT Broker. Return code: {rc}")

def on_message(client, userdata, msg):
    """Callback when a message is received on the subscribed MQTT topic."""
    print("[DEBUG] MQTT message received")
    payload_str = msg.payload.decode('utf-8')
    
    # Run the filtering process: Validate JSON -> Check Missing Fields -> Deduplicate
    processed_data = process_and_filter(payload_str)
    
    if processed_data is None:
        # Message was either invalid or a duplicate, filter has logged the reason
        return
    
    # Run the Rule Engine on the validated telemetry
    detected_faults = detect_faults(processed_data)
    
    # Determine the status based on number of faults
    if len(detected_faults) == 0:
        status = "NORMAL"
    else:
        status = ",".join(detected_faults)
        
    # Append status and list of faults to the processed data
    processed_data["status"] = status
    processed_data["faults"] = detected_faults

    print(f"Received telemetry from {processed_data['station_id']}. Status: {status}")

    # If any faults occur, trigger local edge actions
    if len(detected_faults) > 0:
        # Generate Alert and Print to Console
        print("\n" + "!" * 50)
        print(f"ALERT! Substation {processed_data['station_id']} has active faults:")
        for fault in detected_faults:
            print(f" - {fault}")
        print("!" * 50 + "\n")
        
        # Store alert locally (Edge Storage)
        log_alert_locally(processed_data, detected_faults)
        
    # Always forward processed telemetry (with its status) to Cloud (AWS or local mock)
    # This ensures the dashboard receives historical telemetry for continuous charting
    send_to_cloud(processed_data)

def start_subscriber():
    """Starts the Fog Node MQTT subscriber daemon."""
    # Ensure local DB is initialized
    init_local_db()
    
    client = mqtt.Client("PowerGridFogNode")
    client.on_connect = on_connect
    client.on_message = on_message
    client.on_disconnect = on_disconnect

    print(f"Starting Fog Node MQTT Subscriber...")
    print(f"Connecting to broker at {config.MQTT_BROKER}:{config.MQTT_PORT}...")
    try:
        client.connect(config.MQTT_BROKER, config.MQTT_PORT, 60)
    except Exception as e:
        print(f"Could not connect to broker: {e}")
        print("Please check if Mosquitto broker is running.")
        return

    # Keep blocking and listening for MQTT messages
    try:
        client.loop_forever()
    except KeyboardInterrupt:
        print("\nStopping Fog Node subscriber...")
    finally:
        client.disconnect()
        print("Fog Node subscriber stopped.")

if __name__ == "__main__":
    start_subscriber()
