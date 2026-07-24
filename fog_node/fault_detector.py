import sys
import os
# Add script directory to sys.path to resolve local imports cleanly
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from config import RULES

def detect_faults(data):
    """
    Executes edge computing rules on raw telemetry data.
    Returns a list of fault labels if any rules are violated.
    """
    faults = []

    # 1. Voltage Rule
    voltage = data.get("voltage")
    if voltage is not None:
        if voltage < RULES["voltage"]["low_threshold"]:
            faults.append("LOW_VOLTAGE")
        elif voltage > RULES["voltage"]["high_threshold"]:
            faults.append("HIGH_VOLTAGE")

    # 2. Current Rule
    current = data.get("current")
    if current is not None:
        if current > RULES["current"]["max_threshold"]:
            faults.append("OVER_CURRENT")

    # 3. Frequency Rule
    frequency = data.get("frequency")
    if frequency is not None:
        if frequency < RULES["frequency"]["low_threshold"]:
            faults.append("LOW_FREQUENCY")
        elif frequency > RULES["frequency"]["high_threshold"]:
            faults.append("HIGH_FREQUENCY")

    # 4. Temperature Rule
    temperature = data.get("temperature")
    if temperature is not None:
        if temperature > RULES["temperature"]["max_threshold"]:
            faults.append("OVERHEATING")

    # 5. Load Rule
    load = data.get("load")
    if load is not None:
        if load > RULES["load"]["max_threshold"]:
            faults.append("OVERLOAD")

    return faults
