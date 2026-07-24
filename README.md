# National Power Grid Monitor using Fog and Edge Computing

An IoT, Fog, and Cloud Computing architecture designed to monitor regional electrical substations in real-time. This project simulates sensor telemetry (Voltage, Current, Frequency, Transformer Temperature, and Load), filters data and detects anomalies at the Fog Layer, forwards processed telemetry to AWS Serverless components, and renders a live tracking dashboard.

---

## Project Overview

Directly forwarding high-frequency raw telemetry from thousands of grid sensors to cloud databases creates massive data ingestion bills, consumes high network bandwidth, and results in latency delays. 

This project implements a **Fog Computing Architecture** to address this. The local Fog Node:
1. Receives raw sensor payloads via high-speed MQTT.
2. Validates JSON payload structures and handles missing data.
3. Implements temporal deduplication to eliminate redundant identical telemetry.
4. Executes a rule-based anomaly detection engine at the edge to print immediate alerts and store critical events locally.
5. Buffers and uploads processed telemetry safely to the cloud (AWS or Local SQLite simulation).

---

## System Architecture

```
Power Substations (PS001 - PS005)
      ↓ (Generates sensor values: Voltage, Current, Frequency, Temperature, Load)
Python Telemetry Simulator (sensor_node/sensors.py)
      ↓ (MQTT Topic: power/grid/data)
Mosquitto MQTT Broker (localhost:1883)
      ↓ (Subscribes to Topic)
Fog Node Daemon (fog_node/subscriber.py)
      ↓ (Step 1: Validate -> Step 2: Check Fields -> Step 3: Deduplicate -> Step 4: Rule Engine)
      ↓ (Writes active alerts to Local SQLite database: fog_alerts.db)
      ↓ (HTTP POST to Gateway)
AWS API Gateway
      ↓
AWS Lambda (Ingest Handler)
      ↓ (Pushes to Queue)
Amazon SQS Queue
      ↓ (Triggers)
AWS Lambda (Processor Worker)
      ↓ (Writes database items)
Amazon DynamoDB Tables (SensorData & FaultLogs)
      ↓ (Queries table items)
Flask Web Dashboard (dashboard/app.py)
      ↓ (Chart.js live plots updated every 5s)
HTML5 / CSS3 / Bootstrap 5 / JavaScript
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
│   ├── config.py           # Threshold boundaries, SQLite path, AWS Mode toggle
│   ├── data_filter.py      # JSON validator, field inspector, sliding window cache
│   ├── fault_detector.py   # Edge rule engine (LOW_VOLTAGE, OVERHEAT, etc.)
│   ├── api_client.py       # Cloud forwarder client (API Gateway POST or Mock DB)
│   ├── subscriber.py       # Main MQTT subscription worker and local alert logger
│   └── app.py              # Local edge API to inspect edge metrics/alerts
│
├── cloud/
│   └── lambda_function.py  # AWS Lambda function scripts (Ingestion & SQS Worker)
│
├── dashboard/
│   ├── app.py              # Flask server querying database and serving web page routes
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

## Installation & Setup

### 1. Prerequisite: Mosquitto MQTT Broker
The system requires an active MQTT Broker running locally to manage pub/sub communications.

- **Windows**:
  1. Download the installer from the official page: [https://mosquitto.org/download/](https://mosquitto.org/download/)
  2. Run the installer and complete the setup wizard.
  3. Start the broker by opening Command Prompt as Administrator and running:
     ```cmd
     net start mosquitto
     ```
- **macOS** (via Homebrew):
  ```bash
  brew install mosquitto
  brew services start mosquitto
  ```
- **Linux** (Debian/Ubuntu):
  ```bash
  sudo apt-get update
  sudo apt-get install mosquitto mosquitto-clients
  sudo systemctl start mosquitto
  ```

### 2. Python Packages Installation
Create a Python virtual environment and install the required modules.

```bash
# Create virtual environment
python -m venv venv

# Activate virtual environment
# Windows (PowerShell):
.\venv\Scripts\Activate.ps1
# macOS/Linux:
source venv/bin/activate

# Install dependencies
pip install -r requirements.txt
```

---

## AWS Configuration (Production Deployments)

To transition from the local mock environment to production AWS:

1. **DynamoDB Setup**:
   Create two DynamoDB tables in your selected AWS region:
   - **`SensorData`**: Set Partition Key to `station_id` (String) and Sort Key to `timestamp` (String).
   - **`FaultLogs`**: Set Partition Key to `station_id` (String) and Sort Key to `timestamp` (String).

2. **Amazon SQS Setup**:
   Create a standard SQS queue named `grid-data-queue` and copy its Queue URL.

3. **AWS Lambda Setup**:
   - Create a Lambda function with the code from `cloud/lambda_function.py`.
   - Set up two handler entry points:
     - Assign `lambda_function.lambda_handler_api` to the REST API ingestion trigger.
     - Assign `lambda_function.lambda_handler_sqs` to the SQS queue trigger.
   - Configure Lambda environment variables:
     - `SQS_QUEUE_URL`: Your SQS Queue URL
     - `SENSOR_TABLE`: `SensorData`
     - `FAULT_TABLE`: `FaultLogs`
   - Ensure the Lambda IAM role has policies granting permissions for: `sqs:SendMessage`, `sqs:ReceiveMessage`, `sqs:DeleteMessage`, `sqs:GetQueueAttributes`, `dynamodb:PutItem`, and `dynamodb:Scan`/`dynamodb:Query`.

4. **AWS API Gateway**:
   Create a REST API Gateway that proxies HTTP `POST` requests to the `lambda_handler_api` function. Copy the deployment invoke URL.

5. **Fog Config Update**:
   Open [fog_node/config.py](file:///d:/Power%20Grid%20Monitor/fog_node/config.py) and update the settings:
   ```python
   AWS_MOCK_MODE = False
   AWS_API_GATEWAY_URL = "https://your-api-gateway-id.execute-api.us-east-1.amazonaws.com/prod/telemetry"
   ```

---

## Running the Project

For testing purposes, the project is configured to run in **LOCAL MOCK MODE** out of the box. This saves telemetry to a local mock cloud database file (`mock_cloud_data.db`) without requiring active AWS accounts.

Follow these steps in separate terminal windows (make sure your virtual environment is active in each):

### Step 1: Start the Fog Node Subscriber Daemon
This process runs in the background, listening for MQTT telemetry, running validation filters and fault-detection, and storing data.
```bash
python fog_node/subscriber.py
```

### Step 2: Start the Fog Node Local API (Optional)
Exposes local edge logs on port 5001.
```bash
python fog_node/app.py
```

### Step 3: Start the Sensor Node Simulator
Simulates grid readings for 5 substations and publishes to MQTT. You will see occasional faults injected.
```bash
python sensor_node/publisher.py
```

### Step 4: Run the Flask Web Dashboard
Launches the browser visual monitor interface.
```bash
python dashboard/app.py
```
Open your browser and navigate to **`http://localhost:5000`** to view the live dashboard!

---

## Running Mock Cloud vs AWS Production

### Running Mock Cloud Mode
By default, `AWS_MOCK_MODE` is set to `True` in `fog_node/config.py`.
- In this mode, telemetry data is routed by `fog_node/api_client.py` directly into a local SQLite database named `mock_cloud_data.db` in the workspace root.
- The Flask Dashboard (`dashboard/app.py`) queries this SQLite database instead of DynamoDB.
- **This allows full pipeline demonstration without any AWS account or internet connection.**

### Running AWS Production Version
1. Complete the setup under **AWS Configuration**.
2. Set `AWS_MOCK_MODE = False` in `fog_node/config.py`.
3. Startup the broker, the `fog_node/subscriber.py` subscriber, and the `sensor_node/publisher.py` simulator.
4. Run the Dashboard (`dashboard/app.py`) with AWS credentials configured in your environment (`AWS_ACCESS_KEY_ID`, `AWS_SECRET_ACCESS_KEY`, etc. or via `aws configure`).
5. Processed data will flow: Publisher -> MQTT Broker -> subscriber.py -> AWS API Gateway -> Lambda (Ingest) -> SQS -> Lambda (Worker) -> DynamoDB -> Flask Dashboard.

---

## Troubleshooting

### 1. MQTT Broker Connection Failure (`Could not connect to broker`)
* **Problem**: The publisher or subscriber crashes immediately complaining it cannot connect to `localhost`.
* **Fix**: Ensure Mosquitto is active on port 1883.
  - On Windows: Run `net start mosquitto` in command prompt (as Administrator), or open `Services.msc`, locate "Mosquitto Broker" and start it.
  - On Linux/macOS: Run `sudo systemctl status mosquitto` or `brew services list` to verify.

### 2. Port Conflicts (`Address already in use`)
* **Problem**: Flask app fails to start with port errors on `5000` or `5001`.
* **Fix**: 
  - Port `5000` is the Dashboard. If it is occupied, run it on a different port (e.g. `5002`) by modifying the last line of `dashboard/app.py`: `app.run(host='0.0.0.0', port=5002, debug=True)`.
  - Port `5001` is the local Fog Node API. If occupied, update `FOG_PORT = 5001` in `fog_node/config.py`.

### 3. Missing Database Files
* **Problem**: Dashboard fails to load or charts are blank.
* **Fix**: Run the publisher and subscriber for at least 10 seconds. Telemetry must be published first for `mock_cloud_data.db` to get created automatically in the workspace root directory.

### 4. DynamoDB Decimal Errors
* **Problem**: AWS Lambda or boto3 throws a validation error: `class 'float' not supported`.
* **Fix**: The Lambda script utilizes the `to_decimal()` helper to convert float readings into Python `Decimal` objects before sending to DynamoDB tables. Ensure this helper is not skipped.

---

## Final Project Demonstration Checklist

Before submitting or presenting the project, verify the following:
1. [ ] **Mosquitto** broker is active and listening.
2. [ ] **Fog Subscriber** is running and displaying console output whenever MQTT packets arrive.
3. [ ] **Sensor Node** is running and injecting random faults (look for `[FAULT INJECTED]` printed to output).
4. [ ] **SQLite files** (`fog_alerts.db` inside `fog_node/` and `mock_cloud_data.db` in workspace root) are automatically created.
5. [ ] **Flask Dashboard** shows historical trends on line charts for all 5 stations and the recent alerts list updating every 5 seconds.

