import sys
import os

# Ensure the app root is on sys.path regardless of CWD or PYTHONPATH.
# Uses __file__ so this works however gunicorn is invoked by EB.
_app_root = os.path.dirname(os.path.abspath(__file__))
for _p in (_app_root, os.path.join(_app_root, "dashboard")):
    if _p not in sys.path:
        sys.path.insert(0, _p)

from application import application as app

application = app
