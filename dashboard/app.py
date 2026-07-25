# app.py - Flask Dashboard Server for National Power Grid Monitor
from flask import Flask, render_template, jsonify, request
import os
import sys

# Add parent directory and fog_node to path to share configurations
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
import fog_node.config as config

# Import AWS boto3 for production mode
try:
    import boto3
    from boto3.dynamodb.conditions import Key
except ImportError:
    boto3 = None
    print("WARNING: boto3 is not installed. DynamoDB features will not work.")

app = Flask(__name__)

def fetch_aws_telemetry(limit=10, station_id=None):
    """Queries AWS DynamoDB for telemetry data."""
    if boto3 is None:
        print("boto3 not installed, returning empty telemetry")
        return []
        
    try:
        dynamodb = boto3.resource('dynamodb', region_name=config.AWS_REGION)
        table = dynamodb.Table('SensorData')
        
        if station_id:
            # Query by station partition key, sorting descending by timestamp
            response = table.query(
                KeyConditionExpression=Key('station_id').eq(station_id),
                ScanIndexForward=False,
                Limit=limit
            )
            items = response.get('Items', [])
        else:
            # For dashboard overview, perform a scan (or query all stations)
            # In a small grid, scanning recent data is sufficient for student demo
            response = table.scan(Limit=limit * 5)
            items = response.get('Items', [])
            # Sort items by timestamp descending
            items = sorted(items, key=lambda x: x['timestamp'], reverse=True)
            
        # Convert Decimal values back to float/int for JSON serialization
        formatted_data = []
        for item in items:
            formatted_data.append({
                "station_id": item["station_id"],
                "voltage": float(item.get("voltage", 0)),
                "current": float(item.get("current", 0)),
                "frequency": float(item.get("frequency", 0)),
                "temperature": float(item.get("temperature", 0)),
                "load": float(item.get("load", 0)),
                "status": item.get("status", "NORMAL"),
                "timestamp": item["timestamp"]
            })
        return formatted_data
    except Exception as e:
        print(f"AWS DynamoDB error: {e}")
        return []

def fetch_aws_alerts(limit=50):
    """Queries AWS DynamoDB for fault logs."""
    if boto3 is None:
        return []
    try:
        dynamodb = boto3.resource('dynamodb', region_name=config.AWS_REGION)
        table = dynamodb.Table('FaultLogs')
        response = table.scan(Limit=limit)
        items = response.get('Items', [])
        items = sorted(items, key=lambda x: x['timestamp'], reverse=True)
        return items
    except Exception as e:
        print(f"AWS DynamoDB alert error: {e}")
        return []

# ====================================================
# WEB PAGES ROUTES (Frontend View Controllers)
# ====================================================

@app.route('/')
def dashboard():
    """Renders main dashboard overview page."""
    return render_template('dashboard.html', active_page='dashboard')

@app.route('/stations')
def stations():
    """Renders details page for power substations."""
    selected_id = request.args.get('station_id', 'PS001')
    return render_template(
        'station.html', 
        active_page='stations', 
        station_id=selected_id, 
        all_stations=config.RULES.get('stations', ["PS001", "PS002", "PS003", "PS004", "PS005"])
    )

@app.route('/alerts')
def alerts():
    """Renders alert logs history page."""
    return render_template('dashboard.html', active_page='alerts')

# ====================================================
# BACKEND JSON APIs (Called by static/js/dashboard.js)
# ====================================================

@app.route('/api/telemetry', methods=['GET'])
def api_telemetry():
    """Returns telemetry data array for dashboard visualisations."""
    station_id = request.args.get('station_id')
    limit = int(request.args.get('limit', 10))
    
    data = fetch_aws_telemetry(limit, station_id)
    return jsonify(data)

@app.route('/api/alerts', methods=['GET'])
def api_alerts():
    """Returns fault log array for lists/tables."""
    limit = int(request.args.get('limit', 50))
    
    data = fetch_aws_alerts(limit)
    return jsonify(data)

@app.route('/api/grid_status', methods=['GET'])
def api_grid_status():
    """Aggregates latest status for each station to show summary counts."""
    telemetry = fetch_aws_telemetry(limit=30)
        
    # Get the latest reading for each station ID
    latest_readings = {}
    for read in telemetry:
        sid = read['station_id']
        if sid not in latest_readings:
            latest_readings[sid] = read
            
    # Calculate counters
    total_stations = 5  # PS001 to PS005
    healthy_count = 0
    warning_count = 0
    critical_count = 0
    
    for sid in ["PS001", "PS002", "PS003", "PS004", "PS005"]:
        if sid in latest_readings:
            status = latest_readings[sid]['status']
            if status == "NORMAL":
                healthy_count += 1
            elif status in ["Warning", "LOW_VOLTAGE", "HIGH_VOLTAGE", "OVER_CURRENT", "UNDER_FREQUENCY", "OVERHEATING", "OVERLOAD"]:
                warning_count += 1
            else:
                critical_count += 1
        else:
            # No reading yet, default to healthy or offline (let's assume healthy for display setup)
            healthy_count += 1
            
    return jsonify({
        "total_stations": total_stations,
        "healthy": healthy_count,
        "warning": warning_count,
        "critical": critical_count,
        "latest_readings": latest_readings
    })

if __name__ == '__main__':
    print("Starting Flask Web Dashboard on http://localhost:5000")
    app.run(host='0.0.0.0', port=5000, debug=True)
