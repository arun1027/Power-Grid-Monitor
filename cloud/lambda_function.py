# lambda_function.py - AWS Lambda Ingest & Processing Functions
import json
import os
import boto3
from decimal import Decimal

# Initialize AWS SDK clients
sqs = boto3.client('sqs')
dynamodb = boto3.resource('dynamodb')

# Read AWS resource locations from Environment Variables
QUEUE_URL = os.environ.get('SQS_QUEUE_URL', 'https://sqs.us-east-1.amazonaws.com/your-account-id/grid-data-queue')
SENSOR_TABLE_NAME = os.environ.get('SENSOR_TABLE', 'SensorData')
FAULT_TABLE_NAME = os.environ.get('FAULT_TABLE', 'FaultLogs')

def to_decimal(val):
    """
    Helper to convert float values to Decimal.
    DynamoDB boto3 client requires Decimal format instead of float.
    """
    if isinstance(val, (float, int)):
        return Decimal(str(val))
    return val

def lambda_handler_api(event, context):
    """
    API Ingest Gateway Handler (Lambda 1)
    Triggered by HTTP POST on AWS API Gateway from the Fog Node.
    Puts the validated telemetry message into Amazon SQS for decoupling.
    """
    try:
        # Extract and parse body payload
        body = event.get("body", "{}")
        if isinstance(body, str):
            data = json.loads(body)
        else:
            data = body
            
        print(f"Received API Gateway event for Station: {data.get('station_id')}")
        
        # Enqueue the processed message into SQS
        response = sqs.send_message(
            QueueUrl=QUEUE_URL,
            MessageBody=json.dumps(data)
        )
        
        # Return 202 Accepted status
        return {
            "statusCode": 202,
            "headers": {
                "Content-Type": "application/json",
                "Access-Control-Allow-Origin": "*"  # CORS support
            },
            "body": json.dumps({
                "message": "Grid telemetry accepted and queued in SQS.",
                "message_id": response.get("MessageId")
            })
        }
    except Exception as e:
        print(f"Error in lambda_handler_api: {str(e)}")
        return {
            "statusCode": 500,
            "headers": {
                "Content-Type": "application/json",
                "Access-Control-Allow-Origin": "*"
            },
            "body": json.dumps({"error": f"Failed to ingest data: {str(e)}"})
        }

def lambda_handler_sqs(event, context):
    """
    SQS Worker Handler (Lambda 2)
    Triggered by SQS Queue records.
    Extracts the telemetry records and saves them into DynamoDB tables.
    """
    sensor_table = dynamodb.Table(SENSOR_TABLE_NAME)
    fault_table = dynamodb.Table(FAULT_TABLE_NAME)
    
    records = event.get('Records', [])
    print(f"Processing {len(records)} message records from SQS Queue...")
    
    success_count = 0
    for record in records:
        try:
            # Parse SQS message body containing our telemetry payload
            payload = json.loads(record['body'])
            station_id = payload["station_id"]
            timestamp = payload["timestamp"]
            status = payload.get("status", "Healthy")
            
            print(f"Processing SQS queue record for {station_id} ({timestamp})")
            
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
            
            # If the record contains faults (status is Warning or Critical), save to FaultLogs
            if status != "Healthy":
                faults = payload.get("faults", [])
                fault_item = {
                    "station_id": station_id,
                    "timestamp": timestamp,
                    "faults": faults
                }
                fault_table.put_item(Item=fault_item)
                print(f"Alert state logged in DynamoDB FaultLogs for {station_id}: {faults}")
                
            success_count += 1
            
        except Exception as e:
            print(f"Failed to process SQS record item: {str(e)}")
            # Log error. In production, we'd raise the exception to keep the message in queue,
            # or trigger a Dead Letter Queue (DLQ).
            
    print(f"Queue batch finished. Successfully wrote {success_count}/{len(records)} records to DynamoDB.")
    return {
        "statusCode": 200,
        "body": f"Successfully processed {success_count} queue items."
    }
