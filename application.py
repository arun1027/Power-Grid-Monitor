# application.py - AWS Elastic Beanstalk Entry Point
import os
import sys

# Ensure root and dashboard directories are on Python module search path
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
sys.path.append(BASE_DIR)
sys.path.append(os.path.join(BASE_DIR, "dashboard"))

# Import Flask app instance from dashboard/app.py
from dashboard.app import app as application


def get_app_port() -> int:
    return int(os.getenv("PORT", "8000"))


if __name__ == "__main__":
    application.run(host="0.0.0.0", port=get_app_port())
