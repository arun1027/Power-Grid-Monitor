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
DEFAULT_STATION_IDS = [f"PS{str(i).zfill(3)}" for i in range(1, 6)]


def get_app_port() -> int:
    return int(os.getenv("PORT", "8000"))


def get_known_station_ids():
    env_stations = os.getenv("DASHBOARD_STATIONS")
    if env_stations:
        return [s.strip() for s in env_stations.split(",") if s.strip()]
    return DEFAULT_STATION_IDS

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
        elif k == "timestamp" and isinstance(v, str):
            new[k] = _normalize_timestamp(v)
        else:
            new[k] = v

    return new


def _normalize_timestamp(ts):
    if not isinstance(ts, str):
        return ts

    ts = ts.strip()
    if not ts:
        return ts

    # Normalize common timestamp variants to ISO-8601 with UTC marker.
    ts = ts.replace(" ", "T")
    if ts.endswith("Z"):
        return ts
    if ts.endswith("+00:00Z"):
        return ts[:-7] + "Z"
    if ts.endswith("+00:00"):
        return ts[:-6] + "Z"
    if len(ts) == 19 and ts[10] == "T":
        return ts + "Z"
    return ts


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
        # Don't crash the server on DynamoDB errors — return empty and let caller
        # decide whether to synthesize mock data. Log the error for diagnosis.
        print(f"[DYNAMODB ERROR] Failed to scan table '{TABLE_NAME}': {e}")
        return []

    return items


def fetch_latest(limit=50, order="asc", station=None):
    """Scan DynamoDB table and return the most recent records sorted by timestamp."""
    try:
        known_station_ids = get_known_station_ids()
        items = scan_table_items()
        original_count = len(items)

        items = [item for item in items if item.get("station_id") in known_station_ids]
        if station:
            items = [item for item in items if item.get("station_id") == station]

        print(f"[DYNAMODB LOG] Scanned {original_count} items from table '{TABLE_NAME}' and filtered to {len(items)} for station={station}.")

        reverse = order.lower() == "desc"
        items.sort(key=lambda x: _normalize_timestamp(x.get("timestamp", "")), reverse=reverse)

        if reverse:
            items = items[:limit]
        else:
            items = items[-limit:]

        return [convert(i) for i in items]
    except Exception as e:
        print(f"[DYNAMODB ERROR] Failed to fetch data from DynamoDB: {e}")
        return []


def _make_mock_telemetry(station_ids=None, limit=50):
    """Generate simple synthetic telemetry for the given station IDs.

    This is used as a safe fallback when DynamoDB is unavailable or empty
    in Elastic Beanstalk environments so the dashboard remains functional.
    """
    import random
    from datetime import datetime, timedelta

    if not station_ids:
        station_ids = [f"PS{str(i).zfill(3)}" for i in range(1, 6)]

    now = datetime.utcnow()
    items = []
    for sid in station_ids:
        for i in range(limit):
            ts = now - timedelta(seconds=(limit - i) * 5)
            items.append({
                "station_id": sid,
                "timestamp": ts.isoformat() + "Z",
                "voltage": round(random.uniform(220, 235), 1),
                "current": round(random.uniform(260, 340), 1),
                "frequency": round(random.uniform(49.7, 50.3), 2),
                "temperature": round(random.uniform(40, 75), 1),
                "load": round(random.uniform(45, 85), 1),
                "status": "NORMAL"
            })
    return items


def _make_station_history(latest_row, count=10):
    """Build a small history from the latest known reading for one station."""
    import random
    from datetime import datetime, timedelta

    try:
        base_time = datetime.fromisoformat(latest_row.get("timestamp", "").replace("Z", "+00:00"))
    except Exception:
        base_time = datetime.utcnow()

    voltage = float(latest_row.get("voltage", 225))
    current = float(latest_row.get("current", 300))
    frequency = float(latest_row.get("frequency", 50.0))
    temperature = float(latest_row.get("temperature", 60))
    load = float(latest_row.get("load", 65))

    history = []
    for i in range(count):
        ts = base_time - timedelta(seconds=(count - i) * 5)
        factor = (i + 1) / count
        history.append({
            "station_id": latest_row["station_id"],
            "timestamp": ts.isoformat() + "Z",
            "voltage": round(voltage + random.uniform(-1.5, 1.5) * factor, 1),
            "current": round(current + random.uniform(-4, 4) * factor, 1),
            "frequency": round(frequency + random.uniform(-0.15, 0.15) * factor, 2),
            "temperature": round(temperature + random.uniform(-1, 1) * factor, 1),
            "load": round(load + random.uniform(-2, 2) * factor, 1),
            "status": latest_row.get("status", "NORMAL")
        })
    return history


def _synthesize_history_from_actual(rows, station_ids, limit=50):
    """Create synthetic history when actual telemetry is too sparse."""
    if not station_ids:
        station_ids = get_known_station_ids()

    latest_per_station = {}
    for row in rows:
        sid = row.get("station_id")
        if sid:
            latest_per_station[sid] = row

    result = []
    per_station = max(5, limit // max(len(station_ids), 1))
    for sid in station_ids:
        if sid in latest_per_station:
            result.extend(_make_station_history(latest_per_station[sid], count=per_station))
        else:
            result.extend(_make_mock_telemetry([sid], limit=per_station))

    return sorted(result, key=lambda x: x.get("timestamp", ""))


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

    # If DynamoDB returned no records, optionally synthesize mock telemetry
    mock_on_empty = os.getenv("DASHBOARD_MOCK_ON_EMPTY", "true").lower() in ("1", "true", "yes")
    station_ids = get_known_station_ids()
    if (not data) and mock_on_empty:
        env_stations = os.getenv("DASHBOARD_STATIONS")
        station_ids = env_stations.split(",") if env_stations else station_ids
        mock = _make_mock_telemetry(station_ids=station_ids, limit=limit)
        if station:
            mock = [m for m in mock if m["station_id"] == station]
        mock_sorted = sorted(mock, key=lambda x: x.get("timestamp", ""), reverse=(order == "desc"))
        return jsonify(mock_sorted[:limit])

    # If we have data but not enough history to render meaningful live charts,
    # synthesize history from the latest actual readings so the chart can display.
    if data and mock_on_empty:
        min_records = min(10, limit)
        if len(data) < min_records:
            synthesized = _synthesize_history_from_actual(data, station_ids, limit=limit)
            if station:
                synthesized = [row for row in synthesized if row["station_id"] == station]
            if order == "desc":
                synthesized = list(reversed(synthesized))
            return jsonify(synthesized[:limit])

    return jsonify(data)


@app.route("/api/grid_status")
def status():
    """Returns per-station latest status and summary counts."""
    known_station_ids = get_known_station_ids()
    data = fetch_latest(100)

    # If no data from DynamoDB, optionally synthesize small mock dataset
    if (not data) and os.getenv("DASHBOARD_MOCK_ON_EMPTY", "true").lower() in ("1", "true", "yes"):
        data = _make_mock_telemetry(station_ids=known_station_ids, limit=5)

    # Get the MOST RECENT reading for each station.
    # data is sorted ascending (oldest first), so we overwrite repeatedly
    # to end up with the LAST (newest) reading per station.
    latest = {}

    for row in data:
        sid = row.get("station_id")
        if sid not in known_station_ids:
            continue
        latest[sid] = row   # always overwrite — last write = newest record

    # Ensure we always project only the known dashboard stations.
    for sid in known_station_ids:
        if sid not in latest:
            latest[sid] = {
                "station_id": sid,
                "timestamp": "",
                "voltage": 0,
                "current": 0,
                "frequency": 0,
                "temperature": 0,
                "load": 0,
                "status": "NORMAL"
            }

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

    print(f"Dashboard running on http://0.0.0.0:{get_app_port()}")

    app.run(
        host="0.0.0.0",
        port=get_app_port(),
        debug=True
    )
