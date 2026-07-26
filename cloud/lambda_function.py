# lambda_function.py - AWS Lambda IoT Core Processor
import json
import os
import boto3
from decimal import Decimal

# Initialize DynamoDB client
dynamodb = boto3.resource('dynamodb')

# Table names - set via Lambda environment variables or defaults here
SENSOR_TABLE_NAME = os.environ.get('SENSOR_TABLE', 'PowerGridTelemetry')
FAULT_TABLE_NAME = os.environ.get('FAULT_TABLE', 'FaultLogs')

def to_decimal(val):
    """
    Helper to convert float values to Decimal.
    DynamoDB boto3 client requires Decimal format instead of float.
    """
    if isinstance(val, (float, int)):
        return Decimal(str(val))
    return val

def lambda_handler(event, context):
    """
    IoT Rule Handler
    Triggered directly by AWS IoT Core Rule.
    Extracts the telemetry record (provided in the event JSON) and saves it into DynamoDB tables.
    """
    sensor_table = dynamodb.Table(SENSOR_TABLE_NAME)
    fault_table = dynamodb.Table(FAULT_TABLE_NAME)
    
    try:
        # For IoT rule, the event itself is the JSON payload published to the topic
        payload = event
        
        station_id = payload.get("station_id")
        if not station_id:
            raise ValueError("Payload missing required field: station_id")
            
        timestamp = payload.get("timestamp")
        status = payload.get("status", "NORMAL")
        
        print(f"Processing IoT Rule record for {station_id} at {timestamp}")
        
        # Map float sensor values to Decimals for DynamoDB compatibility
        db_item = {
            "station_id": station_id,
            "timestamp": timestamp,
            "voltage": to_decimal(payload.get("voltage")),
            "current": to_decimal(payload.get("current")),
            "frequency": to_decimal(payload.get("frequency")),
            "temperature": to_decimal(payload.get("temperature")),
            "load": to_decimal(payload.get("load")),
            "status": status
        }
        
        # Write record to the main SensorData DynamoDB table
        sensor_table.put_item(Item=db_item)
        
        # If the record contains faults, save to FaultLogs table
        if status != "NORMAL":
            faults = payload.get("faults", [])
            fault_item = {
                "station_id": station_id,
                "timestamp": timestamp,
                "faults": faults
            }
            fault_table.put_item(Item=fault_item)
            print(f"Alert state logged in DynamoDB FaultLogs for {station_id}: {faults}")
            
        print("Successfully wrote IoT record to DynamoDB.")
        return {
            "statusCode": 200,
            "body": json.dumps({"message": "Successfully processed IoT record."})
        }
    except Exception as e:
        print(f"Failed to process IoT record: {str(e)}")
        return {
            "statusCode": 500,
            "body": json.dumps({"error": str(e)})
        }
