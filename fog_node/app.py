# app.py - Flask application representing the Fog Node's Web API interface
import sys
import os
# Add script directory to sys.path to resolve local imports cleanly
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from flask import Flask, jsonify, request
import sqlite3
import config

app = Flask(__name__)

def get_db_connection():
    """Helper to connect to the local SQLite edge database."""
    conn = sqlite3.connect(config.LOCAL_DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn

@app.route('/')
def index():
    """Root route showing status of the Edge Fog Node."""
    return jsonify({
        "node_id": "FOG_EAST_01",
        "status": "Online",
        "mqtt_broker": config.MQTT_BROKER,
        "mqtt_topic": config.MQTT_TOPIC,
        "mock_cloud_active": config.AWS_MOCK_MODE,
        "endpoints": {
            "/": "Fog Node configuration status",
            "/alerts": "List of active alerts generated locally",
            "/health": "Detailed health diagnostics"
        }
    })

@app.route('/alerts', methods=['GET'])
def get_alerts():
    """Exposes local alerts logged at the edge."""
    # Check if database exists
    if not os.path.exists(config.LOCAL_DB_PATH):
        return jsonify([])
        
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM LocalAlerts ORDER BY timestamp DESC LIMIT 50")
        rows = cursor.fetchall()
        conn.close()
        
        alerts = []
        for r in rows:
            alerts.append({
                "id": r["id"],
                "station_id": r["station_id"],
                "faults": r["faults"].split(", ") if r["faults"] else [],
                "voltage": r["voltage"],
                "current": r["current"],
                "frequency": r["frequency"],
                "temperature": r["temperature"],
                "load": r["load"],
                "timestamp": r["timestamp"]
            })
            
        return jsonify(alerts)
    except Exception as e:
        return jsonify({"error": f"Failed to retrieve local alerts: {e}"}), 500

@app.route('/health', methods=['GET'])
def health():
    """Simple diagnostic endpoint for the Fog Node."""
    db_status = "Available" if os.path.exists(config.LOCAL_DB_PATH) else "Not Initialized"
    return jsonify({
        "status": "Healthy",
        "edge_storage": db_status,
        "rules_configured": list(config.RULES.keys())
    })

if __name__ == '__main__':
    print(f"Starting Fog Node local API on http://localhost:{config.FOG_PORT}")
    app.run(host=config.FOG_HOST, port=config.FOG_PORT, debug=True)
