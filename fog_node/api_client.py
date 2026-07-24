# api_client.py - Sends processed telemetry and faults to Cloud
import requests
import json
import sqlite3
from datetime import datetime
import config

# Define mock cloud database file name
import os
MOCK_CLOUD_DB = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "mock_cloud_data.db"))

def init_mock_cloud_db():
    """Initializes the mock cloud database tables if they do not exist."""
    conn = sqlite3.connect(MOCK_CLOUD_DB)
    cursor = conn.cursor()
    
    # SensorData Table
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS SensorData (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            station_id TEXT NOT NULL,
            voltage REAL,
            current REAL,
            frequency REAL,
            temperature REAL,
            load REAL,
            status TEXT,
            timestamp TEXT NOT NULL
        )
    ''')
    
    # FaultLogs Table
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS FaultLogs (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            station_id TEXT NOT NULL,
            faults TEXT NOT NULL,
            timestamp TEXT NOT NULL
        )
    ''')
    conn.commit()
    conn.close()

def send_to_cloud(processed_data):
    """
    Forwards processed telemetry and status payload to AWS.
    If AWS_MOCK_MODE is enabled, writes directly to local mock cloud database.
    """
    if config.AWS_MOCK_MODE:
        return _send_to_mock_cloud(processed_data)
    else:
        return _send_to_aws_api_gateway(processed_data)

def _send_to_mock_cloud(data):
    """Saves data to mock cloud SQLite database simulating AWS ingest."""
    try:
        init_mock_cloud_db()
        conn = sqlite3.connect(MOCK_CLOUD_DB)
        cursor = conn.cursor()
        
        # Insert telemetry into SensorData
        cursor.execute('''
            INSERT INTO SensorData (station_id, voltage, current, frequency, temperature, load, status, timestamp)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        ''', (
            data["station_id"],
            data["voltage"],
            data["current"],
            data["frequency"],
            data["temperature"],
            data["load"],
            data["status"],
            data["timestamp"]
        ))
        
        # If there is a fault, log it in FaultLogs
        if data["status"] != "Healthy":
            # Joint faults as comma-separated string
            fault_str = ",".join(data["faults"])
            cursor.execute('''
                INSERT INTO FaultLogs (station_id, faults, timestamp)
                VALUES (?, ?, ?)
            ''', (data["station_id"], fault_str, data["timestamp"]))
            
        conn.commit()
        conn.close()
        print(f"[API CLIENT - MOCK] Forwarded data for {data['station_id']} to mock cloud database successfully.")
        return True
    except Exception as e:
        print(f"[API CLIENT - MOCK ERROR] Failed to write to mock cloud: {e}")
        return False

def _send_to_aws_api_gateway(data):
    """Sends telemetry data payload to the live AWS API Gateway endpoint."""
    headers = {
        "Content-Type": "application/json",
        # "x-api-key": "your-api-key-here"  # Uncomment if API Gateway requires an API key
    }
    
    try:
        print(f"[API CLIENT] Posting payload to AWS API Gateway: {config.AWS_API_GATEWAY_URL}...")
        response = requests.post(
            config.AWS_API_GATEWAY_URL, 
            data=json.dumps(data), 
            headers=headers,
            timeout=10
        )
        
        if response.status_code in [200, 201, 202]:
            print(f"[API CLIENT] AWS API accepted payload. Status: {response.status_code}")
            return True
        else:
            print(f"[API CLIENT ERROR] AWS API Gateway returned status {response.status_code}: {response.text}")
            return False
            
    except requests.exceptions.RequestException as e:
        print(f"[API CLIENT ERROR] Failed to connect to AWS API Gateway: {e}")
        print("Tip: Enable AWS_MOCK_MODE = True in fog_node/config.py to test without live AWS.")
        return False
