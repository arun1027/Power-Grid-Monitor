# sensors.py - Sensor Simulator for Power Stations
import random
import time
from datetime import datetime, timezone
from config import SENSOR_RANGES

def generate_sensor_data(station_id, inject_fault=False):
    """
    Generates a telemetry reading for a given station.
    If inject_fault is True, one of the metrics will be forced into its fault range.
    """
    # 1. Start with normal values generated within configured ranges
    voltage = round(random.uniform(SENSOR_RANGES["voltage"]["min"], SENSOR_RANGES["voltage"]["max"]), 1)
    current = round(random.uniform(SENSOR_RANGES["current"]["min"], SENSOR_RANGES["current"]["max"]), 1)
    frequency = round(random.uniform(SENSOR_RANGES["frequency"]["min"], SENSOR_RANGES["frequency"]["max"]), 2)
    temperature = round(random.uniform(SENSOR_RANGES["temperature"]["min"], SENSOR_RANGES["temperature"]["max"]), 1)
    load = round(random.uniform(SENSOR_RANGES["load"]["min"], SENSOR_RANGES["load"]["max"]), 1)
    
    # 2. If fault injection is triggered, override one metric with an anomaly
    if inject_fault:
        fault_type = random.choice(["voltage_low", "voltage_high", "current_high", "frequency_low", "frequency_high", "temperature_high", "load_high"])
        
        if fault_type == "voltage_low":
            voltage = round(random.uniform(180.0, 209.0), 1)  # below 210
        elif fault_type == "voltage_high":
            voltage = round(random.uniform(251.0, 270.0), 1)  # above 250
        elif fault_type == "current_high":
            current = round(random.uniform(410.0, 500.0), 1)  # above 400
        elif fault_type == "frequency_low":
            frequency = round(random.uniform(47.0, 48.9), 2)  # below 49
        elif fault_type == "frequency_high":
            frequency = round(random.uniform(51.1, 53.0), 2)  # above 51
        elif fault_type == "temperature_high":
            temperature = round(random.uniform(91.0, 120.0), 1)  # above 90
        elif fault_type == "load_high":
            load = round(random.uniform(96.0, 110.0), 1)  # above 95

    # 3. Create the telemetry JSON dictionary
    data = {
        "station_id": station_id,
        "voltage": voltage,
        "current": current,
        "frequency": frequency,
        "temperature": temperature,
        "load": load,
        "timestamp": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%S.%f") + "Z"
    }
    
    return data

if __name__ == "__main__":
    # Small test snippet to verify code works when executed directly
    print("Testing sensor data generation...")
    print("Normal reading:", generate_sensor_data("PS001", inject_fault=False))
    print("Faulty reading:", generate_sensor_data("PS001", inject_fault=True))
