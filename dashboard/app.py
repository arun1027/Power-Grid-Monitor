# app.py - Flask Dashboard Server for National Power Grid Monitor
# Reads directly from AWS DynamoDB PowerGridTelemetry table
from flask import Flask, render_template, jsonify, request
import boto3
from boto3.dynamodb.conditions import Key
from decimal import Decimal
import os

app = Flask(__name__)

# AWS Configuration
AWS_REGION = "us-east-1"
TABLE_NAME = "PowerGridTelemetry"

# Connect to DynamoDB
dynamodb = boto3.resource(
    "dynamodb",
    region_name=AWS_REGION
)

table = dynamodb.Table(TABLE_NAME)


def convert(item):
    """Convert DynamoDB Decimal types to Python int/float for JSON serialization."""
    new = {}

    for k, v in item.items():
        if isinstance(v, Decimal):
            if v % 1 == 0:
                new[k] = int(v)
            else:
                new[k] = float(v)
        else:
            new[k] = v

    return new


def scan_table_items():
    """Scan DynamoDB table fully with pagination."""
    items = []
    try:
        response = table.scan()
        items.extend(response.get("Items", []))
        while response.get("LastEvaluatedKey"):
            response = table.scan(ExclusiveStartKey=response["LastEvaluatedKey"])
            items.extend(response.get("Items", []))
    except Exception as e:
        print(f"[DYNAMODB ERROR] Failed to scan table '{TABLE_NAME}': {e}")
        raise
    return items


def fetch_latest(limit=50, order="asc", station=None):
    """Scan DynamoDB table and return the most recent records sorted by timestamp."""
    try:
        items = scan_table_items()
        original_count = len(items)

        if station:
            items = [item for item in items if item.get("station_id") == station]

        print(f"[DYNAMODB LOG] Scanned {original_count} items from table '{TABLE_NAME}' and filtered to {len(items)} for station={station}.")

        reverse = order.lower() == "desc"
        items.sort(key=lambda x: x.get("timestamp", ""), reverse=reverse)

        if reverse:
            items = items[:limit]
        else:
            items = items[-limit:]

        return [convert(i) for i in items]
    except Exception as e:
        print(f"[DYNAMODB ERROR] Failed to fetch data from DynamoDB: {e}")
        return []


# ====================================================
# PAGE ROUTES
# ====================================================

@app.route("/")
def dashboard():
    """Main dashboard overview page."""
    return render_template("dashboard.html", active_page="dashboard")


@app.route("/stations")
def stations():
    """Per-station detail page."""
    selected_id = request.args.get("station_id", "PS001")
    all_stations = ["PS001", "PS002", "PS003", "PS004", "PS005"]
    return render_template(
        "station.html",
        active_page="stations",
        station_id=selected_id,
        all_stations=all_stations
    )


@app.route("/alerts")
def alerts():
    """Fault history page."""
    return render_template("dashboard.html", active_page="alerts")


# ====================================================
# JSON API ROUTES (called by dashboard.js every 5s)
# ====================================================

@app.route("/api/telemetry")
def telemetry():
    """Returns latest telemetry records, optionally filtered by station_id."""
    station = request.args.get("station_id")
    limit = request.args.get("limit", default=100, type=int)
    order = request.args.get("order", default="asc", type=str).lower()
    if order not in ("asc", "desc"):
        order = "asc"

    data = fetch_latest(limit=limit, order=order, station=station)
    return jsonify(data)


@app.route("/api/grid_status")
def status():
    """Returns per-station latest status and summary counts."""
    data = fetch_latest(100)

    # Get the MOST RECENT reading for each station.
    # data is sorted ascending (oldest first), so we overwrite repeatedly
    # to end up with the LAST (newest) reading per station.
    latest = {}

    for row in data:

        sid = row["station_id"]
        latest[sid] = row   # always overwrite — last write = newest record

    # Count station health states by reading the status field directly
    # status == "NORMAL" -> healthy
    # status contains one fault -> warning
    # status contains multiple faults (comma-separated) -> critical
    healthy = 0
    warning = 0
    critical = 0

    for station in latest.values():
        s = station.get("status", "NORMAL")
        if s == "NORMAL":
            healthy += 1
        elif "," in s:
            # Multiple faults = critical
            critical += 1
        else:
            # Single fault = warning
            warning += 1

    return jsonify({
        "total_stations": len(latest),
        "healthy": healthy,
        "warning": warning,
        "critical": critical,
        "latest_readings": latest
    })


@app.route("/api/alerts")
def api_alerts():
    """Returns all non-NORMAL readings as the fault/alert list."""
    limit = request.args.get("limit", default=200, type=int)
    data = fetch_latest(limit=limit, order="desc")

    alerts = [row for row in data if row.get("status") != "NORMAL"]
    return jsonify(alerts)


if __name__ == "__main__":

    print("Dashboard running on http://0.0.0.0:5000")

    app.run(
        host="0.0.0.0",
        port=5000,
        debug=True
    )
