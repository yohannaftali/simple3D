#!/bin/bash
sudo cp simple3d.service /etc/systemd/system/
sudo systemctl daemon-reload
sudo systemctl enable simple3d
sudo systemctl start simple3d