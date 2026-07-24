# data_filter.py - Validation and Deduplication for Incoming Telemetry Data
import json
import hashlib

# Expected keys in the telemetry JSON message
REQUIRED_FIELDS = ["station_id", "voltage", "current", "frequency", "temperature", "load", "timestamp"]

# Global cache to keep track of recently processed message signatures for deduplication.
# This prevents network retries or duplicate broker sends from polluting the system.
MAX_CACHE_SIZE = 50
recent_messages_cache = []

def validate_json(payload_str):
    """
    Step 1: Validate that the MQTT payload is a valid JSON string.
    Returns the parsed dict if valid, or None if invalid.
    """
    try:
        data = json.loads(payload_str)
        return data
    except json.JSONDecodeError as e:
        print(f"[DATA FILTER ERROR] Payload is not valid JSON: {e}")
        return None

def check_missing_fields(data):
    """
    Step 2: Check if the dictionary has all required sensor and metadata fields.
    Returns True if valid, False if any required fields are missing.
    """
    missing = [field for field in REQUIRED_FIELDS if field not in data]
    if missing:
        print(f"[DATA FILTER ERROR] Message from {data.get('station_id', 'Unknown')} is missing fields: {missing}")
        return False
    return True

def is_duplicate(data):
    """
    Step 3: Remove duplicate messages.
    Creates a unique hash based on the station_id, timestamp, and sensor readings.
    If the hash is in the cache, it's a duplicate. Otherwise, adds it to the cache.
    """
    # Create a unique representation of the message content
    signature = f"{data['station_id']}_{data['timestamp']}_{data['voltage']}_{data['current']}_{data['frequency']}_{data['temperature']}_{data['load']}"
    message_hash = hashlib.md5(signature.encode('utf-8')).hexdigest()

    # Check if we have seen this hash recently
    if message_hash in recent_messages_cache:
        print(f"[DATA FILTER] Duplicate message detected for {data['station_id']} at {data['timestamp']}. Dropping.")
        return True

    # Maintain a sliding window cache size
    recent_messages_cache.append(message_hash)
    if len(recent_messages_cache) > MAX_CACHE_SIZE:
        recent_messages_cache.pop(0)

    return False

def process_and_filter(payload_str):
    """
    Combines the filtration steps.
    Returns the parsed dict if it passes validation, missing fields check, and deduplication.
    Otherwise returns None.
    """
    # Step 1: Validate JSON structure
    data = validate_json(payload_str)
    if not data:
        return None

    # Step 2: Check for missing fields
    if not check_missing_fields(data):
        return None

    # Step 3: Deduplicate
    if is_duplicate(data):
        return None

    return data
