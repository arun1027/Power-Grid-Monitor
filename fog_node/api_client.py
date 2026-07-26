# api_client.py - Sends processed telemetry and faults to Cloud via AWS IoT Core
import json
import ssl
import paho.mqtt.client as mqtt
import config

def on_connect(client, userdata, flags, rc):
    if rc == 0:
        print("[API CLIENT] Successfully connected to AWS IoT Core.")
    else:
        print(f"[API CLIENT ERROR] Failed to connect to AWS IoT Core, return code {rc}")

# Initialize the MQTT client
mqtt_client = mqtt.Client(client_id="FogNodePublisher")

# Configure TLS/SSL and connect
try:
    mqtt_client.tls_set(
        ca_certs=config.ROOT_CA_PATH,
        certfile=config.DEVICE_CERT_PATH,
        keyfile=config.PRIVATE_KEY_PATH,
        cert_reqs=ssl.CERT_REQUIRED,
        tls_version=ssl.PROTOCOL_TLSv1_2,
        ciphers=None
    )
    
    # Connect to AWS IoT Core on port 8883
    print(f"[API CLIENT] Connecting to AWS IoT Core endpoint {config.AWS_IOT_ENDPOINT}...")
    mqtt_client.on_connect = on_connect
    mqtt_client.connect(config.AWS_IOT_ENDPOINT, 8883, keepalive=60)
    mqtt_client.loop_start()  # Start the background network loop
except Exception as e:
    print(f"[API CLIENT ERROR] Failed to setup MQTT TLS or connect: {e}")
    print("Please ensure your certificates exist and the paths in config.py are correct.")

import boto3
from decimal import Decimal

# Initialize DynamoDB client for direct cloud persistence
try:
    dynamodb = boto3.resource('dynamodb', region_name=config.AWS_REGION)
    telemetry_table = dynamodb.Table('PowerGridTelemetry')
    fault_table = dynamodb.Table('FaultLogs')
except Exception as err:
    print(f"[API CLIENT WARNING] DynamoDB client init warning: {err}")
    telemetry_table = None

def _to_decimal(val):
    if isinstance(val, (float, int)):
        return Decimal(str(val))
    return val

def send_to_cloud(processed_data):
    """
    Publishes processed telemetry payload to AWS IoT Core via MQTT over TLS
    AND saves record directly into DynamoDB PowerGridTelemetry for live dashboard tracking.
    """
    success = False

    # 1. Publish to AWS IoT Core MQTT Broker
    try:
        payload_str = json.dumps(processed_data)
        result = mqtt_client.publish(config.AWS_IOT_TOPIC, payload_str, qos=1)
        if result.rc == mqtt.MQTT_ERR_SUCCESS:
            print(f"[API CLIENT] Published to AWS IoT Core topic '{config.AWS_IOT_TOPIC}' for {processed_data.get('station_id')}.")
            success = True
        else:
            print(f"[API CLIENT ERROR] MQTT publish returned error code: {result.rc}")
    except Exception as e:
        print(f"[API CLIENT ERROR] Exception during MQTT publish: {e}")

    # 2. Write to DynamoDB PowerGridTelemetry table for real-time dashboard streaming
    if telemetry_table is not None:
        try:
            item = {
                "station_id": processed_data.get("station_id"),
                "timestamp": processed_data.get("timestamp"),
                "voltage": _to_decimal(processed_data.get("voltage")),
                "current": _to_decimal(processed_data.get("current")),
                "frequency": _to_decimal(processed_data.get("frequency")),
                "temperature": _to_decimal(processed_data.get("temperature")),
                "load": _to_decimal(processed_data.get("load")),
                "status": processed_data.get("status", "NORMAL")
            }
            telemetry_table.put_item(Item=item)
            
            # Log faults if status is non-NORMAL
            if processed_data.get("status") != "NORMAL":
                fault_item = {
                    "station_id": processed_data.get("station_id"),
                    "timestamp": processed_data.get("timestamp"),
                    "faults": processed_data.get("faults", [])
                }
                fault_table.put_item(Item=fault_item)
                
            print(f"[API CLIENT -> DYNAMODB] Saved live reading for {processed_data.get('station_id')} into PowerGridTelemetry.")
            success = True
        except Exception as e:
            print(f"[API CLIENT -> DYNAMODB ERROR] Failed writing to DynamoDB: {e}")

    return success
