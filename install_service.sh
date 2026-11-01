#!/bin/bash
# Install or update the simple3d systemd service (runs server.py on port 8080).
# Safe to re-run; restarting only reloads the web UI, not Klipper/Moonraker.
set -e
cd "$(dirname "$0")"
sudo cp simple3d.service /etc/systemd/system/
sudo systemctl daemon-reload
sudo systemctl enable simple3d
sudo systemctl restart simple3d
systemctl --no-pager status simple3d | head -5
