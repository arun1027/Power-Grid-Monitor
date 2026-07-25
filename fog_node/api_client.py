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

def send_to_cloud(processed_data):
    """
    Publishes processed telemetry and status payload to AWS IoT Core using paho-mqtt.
    """
    try:
        print(f"[API CLIENT] Publishing payload to AWS IoT Core Topic '{config.AWS_IOT_TOPIC}'...")
        
        # Publish payload
        payload_str = json.dumps(processed_data)
        result = mqtt_client.publish(config.AWS_IOT_TOPIC, payload_str, qos=1)
        
        if result.rc == mqtt.MQTT_ERR_SUCCESS:
            print(f"[API CLIENT] Successfully published data for {processed_data.get('station_id')}.")
            return True
        else:
            print(f"[API CLIENT ERROR] Publish returned error code: {result.rc}")
            return False
            
    except Exception as e:
        print(f"[API CLIENT ERROR] Exception during publish: {e}")
        return False
