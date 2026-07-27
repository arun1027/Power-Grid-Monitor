#!/bin/bash
# =========================================================
# Skip EB's automatic pip install of requirements.txt
# All dependencies are pre-listed with pinned versions in
# requirements.txt (including ALL transitive dependencies).
# We use --no-deps to prevent pip from downloading or
# resolving any additional packages from PyPI.
# =========================================================
echo "[DEPLOY] Installing pinned dependencies with --no-deps (no auto-resolution)..."
source /var/app/venv/*/bin/activate 2>/dev/null || true
pip install --no-deps --no-cache-dir -r /var/app/staging/requirements.txt 2>&1 || \
pip install --no-deps --no-cache-dir -r /var/app/current/requirements.txt 2>&1
echo "[DEPLOY] Done. All dependencies installed from pinned requirements.txt"
