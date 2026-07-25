# National Power Grid Monitor using Fog and Edge Computing

An IoT, Fog, and Cloud Computing architecture designed to monitor regional electrical substations in real-time. This project simulates sensor telemetry (Voltage, Current, Frequency, Transformer Temperature, and Load), filters data and detects anomalies at the Fog Layer, forwards processed telemetry securely to AWS IoT Core, and renders a live tracking dashboard.

---

## Project Overview

Directly forwarding high-frequency raw telemetry from thousands of grid sensors to cloud databases creates massive data ingestion bills, consumes high network bandwidth, and results in latency delays. 

This project implements a **Fog Computing Architecture** to address this. The local Fog Node:
1. Receives raw sensor payloads via high-speed MQTT.
2. Validates JSON payload structures and handles missing data.
3. Implements temporal deduplication to eliminate redundant identical telemetry.
4. Executes a rule-based anomaly detection engine at the edge to print immediate alerts and store critical events locally.
5. Buffers and securely uploads only processed telemetry to AWS IoT Core using MQTT over TLS.

---

## Architecture Diagram

```
Sensor Simulator
        │
        ▼
Mosquitto MQTT
        │
        ▼
Fog Node (EC2)
• Filtering
• Edge Processing
• Fault Detection
• SQLite Alerts
• MQTT TLS Publisher
        │
        ▼
AWS IoT Core
        │
        ▼
IoT Rule
        │
        ▼
Lambda
        │
        ▼
DynamoDB
        │
        ▼
Flask Dashboard (Elastic Beanstalk)
```

---

## Folder Structure

```
NationalPowerGridMonitor/
│
├── sensor_node/
│   ├── config.py           # MQTT broker IP, publish intervals, sensor normal ranges
│   ├── sensors.py          # Random value generator with anomaly injector
│   └── publisher.py        # MQTT publishing daemon
│
├── fog_node/
│   ├── certs/              # Holds AWS IoT Core certificates (RootCA, Device Cert, Private Key)
│   ├── config.py           # Threshold boundaries, SQLite path, IoT Core endpoint and paths
│   ├── data_filter.py      # JSON validator, field inspector, sliding window cache
│   ├── fault_detector.py   # Edge rule engine (LOW_VOLTAGE, OVERHEAT, etc.)
│   ├── api_client.py       # MQTT TLS publisher to AWS IoT Core (paho-mqtt)
│   ├── subscriber.py       # Main MQTT subscription worker and local alert logger
│   ├── app.py              # Local edge API to inspect edge metrics/alerts
│   └── fog_alerts.db       # Edge storage database
│
├── cloud/
│   └── lambda_function.py  # AWS Lambda function for IoT Rule data insertion to DynamoDB
│
├── dashboard/
│   ├── app.py              # Flask server querying DynamoDB using boto3
│   ├── static/
│   │   ├── css/
│   │   │   └── style.css   # Custom styling, status badges, micro-animations
│   │   └── js/
│   │       └── dashboard.js # Chart.js charts creation, data polling client
│   └── templates/
│       ├── index.html      # Layout frame with blue navigation navbar
│       ├── dashboard.html  # Live charts grid and recent fault logs tables
│       └── station.html    # Detailed substation graphs and sensor gauges
│
├── requirements.txt        # Third-party library definitions
└── README.md               # Setup and instruction guide
```

---

## Deployment Documentation

This system is fully distributed and designed to run across multiple environments.

### Local Machine (Sensor Layer)
Runs:
- `sensor_node/` - Simulates the hardware sensors on the power substations, publishing MQTT data locally to a Mosquitto broker.

### AWS EC2 (Fog Node Layer)
Runs:
- `fog_node/` - Deployed as a background service on an EC2 instance on the edge of the network.
Includes:
- `certs/` folder with the following AWS IoT certificates:
  - `AmazonRootCA1.pem`
  - `device.pem.crt`
  - `private.pem.key`
The Fog Node performs validation and deduplication, writes faults locally to SQLite, and uses `api_client.py` to publish processed JSON telemetry securely to AWS IoT Core via MQTT over TLS.

### AWS IoT Core
- **Receives MQTT**: Subscribes to the edge data coming in from the Fog Node on port 8883.
- **IoT Rule**: A rule intercepts data on the topic `powergrid/data` and Triggers the Lambda function.
  - *Rule SQL*: `SELECT * FROM 'powergrid/data'`
  - *Action*: Invoke Lambda

### AWS Lambda
- **Stores Data**: Receives the processed JSON event directly from the IoT rule trigger. Extracts the values, converts floats to `Decimal`, and saves the records directly to DynamoDB tables.

### Amazon DynamoDB
- **Stores Telemetry and Faults**:
  - `SensorData` Table: Partition Key = `station_id`, Sort Key = `timestamp`
  - `FaultLogs` Table: Partition Key = `station_id`, Sort Key = `timestamp`

### AWS Elastic Beanstalk (Presentation Layer)
Runs:
- `dashboard/` - A Flask web server displaying live telemetry metrics and alerts using Chart.js.
- Connects directly to DynamoDB via `boto3` to retrieve historical trends, completely bypassing the Fog Node.

---

## Setup & Running Locally for Testing

### 1. Prerequisite: Mosquitto MQTT Broker
The system requires an active MQTT Broker running locally to manage pub/sub communications from the sensor simulator to the fog node.
- **Windows**: Install from [mosquitto.org](https://mosquitto.org/download/) and run `net start mosquitto`.
- **macOS/Linux**: Install via `brew install mosquitto` or `sudo apt-get install mosquitto`.

### 2. Python Packages Installation
```bash
python -m venv venv
.\venv\Scripts\Activate.ps1   # Windows
source venv/bin/activate      # Mac/Linux
pip install -r requirements.txt
```

### 3. AWS Credentials setup
For the dashboard and Fog Node to access AWS, you need to configure your AWS credentials on the deployment machines using the AWS CLI or setting environment variables (`AWS_ACCESS_KEY_ID`, `AWS_SECRET_ACCESS_KEY`, `AWS_DEFAULT_REGION`).

### 4. Running the Components

**Start the Sensor Simulator:**
```bash
python sensor_node/publisher.py
```

**Start the Fog Node Edge Service:**
Ensure your AWS certificates are placed inside `fog_node/certs/` and your AWS IoT Endpoint is configured in `fog_node/config.py`.
```bash
python fog_node/subscriber.py
```

**Start the Flask Dashboard:**
```bash
python dashboard/app.py
```
Open your browser and navigate to **`http://localhost:5000`** to view the live dashboard!
