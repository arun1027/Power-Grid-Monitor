# api_client.py - Sends processed telemetry and faults to Cloud via AWS IoT Core
import json
import os
import ssl
import traceback
import paho.mqtt.client as mqtt
import config

def on_connect(client, userdata, flags, rc):
    if rc == 0:
        print("[API CLIENT] Successfully connected to AWS IoT Core.")
    else:
        print(f"[API CLIENT ERROR] Failed to connect to AWS IoT Core, return code {rc}")


def on_disconnect(client, userdata, rc):
    print(f"[API CLIENT] Disconnected from AWS IoT Core with rc={rc}")


# Initialize the MQTT client
mqtt_client = mqtt.Client(client_id="FogNodePublisher")
mqtt_client.on_connect = on_connect
mqtt_client.on_disconnect = on_disconnect
mqtt_available = False


def _has_aws_iot_certs():
    return (
        os.path.exists(config.ROOT_CA_PATH)
        and os.path.exists(config.DEVICE_CERT_PATH)
        and os.path.exists(config.PRIVATE_KEY_PATH)
    )

if config.AWS_IOT_ENABLED:
    print(f"[API CLIENT] AWS_IOT_ENABLED={config.AWS_IOT_ENABLED}, endpoint={config.AWS_IOT_ENDPOINT}, port={config.AWS_IOT_MQTT_PORT}")
    print(f"[API CLIENT] Cert paths: root={config.ROOT_CA_PATH} exists={os.path.exists(config.ROOT_CA_PATH)}, cert={config.DEVICE_CERT_PATH} exists={os.path.exists(config.DEVICE_CERT_PATH)}, key={config.PRIVATE_KEY_PATH} exists={os.path.exists(config.PRIVATE_KEY_PATH)}")
    if _has_aws_iot_certs():
        try:
            mqtt_client.tls_set(
                ca_certs=config.ROOT_CA_PATH,
                certfile=config.DEVICE_CERT_PATH,
                keyfile=config.PRIVATE_KEY_PATH,
                cert_reqs=ssl.CERT_REQUIRED,
                tls_version=ssl.PROTOCOL_TLSv1_2,
                ciphers=None
            )

            print(f"[API CLIENT] Connecting to AWS IoT Core endpoint {config.AWS_IOT_ENDPOINT}...")
            mqtt_client.connect(config.AWS_IOT_ENDPOINT, config.AWS_IOT_MQTT_PORT, keepalive=60)
            mqtt_client.loop_start()  # Start the background network loop
            mqtt_available = True
        except Exception as e:
            print(f"[API CLIENT ERROR] Failed to setup MQTT TLS or connect: {e}")
            traceback.print_exc()
    else:
        print("[API CLIENT WARNING] AWS IoT certificates missing; AWS IoT publishing disabled.")
else:
    print("[API CLIENT] AWS IoT publishing disabled by configuration.")

import boto3
from decimal import Decimal

telemetry_table = None
fault_table = None

try:
    dynamodb = boto3.resource('dynamodb', region_name=config.AWS_REGION)
    telemetry_table = dynamodb.Table('PowerGridTelemetry')
    fault_table = dynamodb.Table('FaultLogs')
except Exception as err:
    print(f"[API CLIENT WARNING] DynamoDB client init warning: {err}")


def _to_decimal(val):
    if isinstance(val, (float, int)):
        return Decimal(str(val))
    return val

def ensure_mqtt_connection():
    """Ensures the MQTT client is connected before publishing."""
    if not config.AWS_IOT_ENABLED:
        print("[API CLIENT] AWS IoT is disabled; skipping MQTT connect check.")
        return False

    if not mqtt_available:
        print("[API CLIENT] MQTT client unavailable due to setup failure.")
        return False

    if mqtt_client.is_connected():
        return True

    try:
        print("[API CLIENT] MQTT client not connected, attempting reconnect...")
        mqtt_client.reconnect()
        is_connected = mqtt_client.is_connected()
        print(f"[API CLIENT] MQTT reconnect result: {is_connected}")
        return is_connected
    except Exception as e:
        print(f"[API CLIENT ERROR] MQTT reconnect failed: {e}")
        return False


def send_to_cloud(processed_data):
    """
    Publishes processed telemetry payload to AWS IoT Core via MQTT over TLS
    AND saves record directly into DynamoDB PowerGridTelemetry for live dashboard tracking.
    """
    success = False

    # 1. Publish to AWS IoT Core MQTT Broker
    try:
        payload_str = json.dumps(processed_data)

        if not ensure_mqtt_connection():
            print("[API CLIENT WARNING] MQTT client is disconnected; skipping publish.")
        else:
            result = mqtt_client.publish(config.AWS_IOT_TOPIC, payload_str, qos=1)
            print(f"[API CLIENT] MQTT publish result: rc={result.rc}, mid={getattr(result, 'mid', 'unknown')}")
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
