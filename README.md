# simple3D — Klipper Web UI for Legacy Devices

A minimal, single-file HTML web UI for controlling a Klipper 3D printer via the Moonraker API.

Built specifically for **old iOS devices (iOS 10, Safari)** that can no longer run modern UIs like Fluidd or Mainsail. No build tools, no npm, no framework — just one `index.html`.

## Features

- Temperature monitor & control (hotend + bed)
- Print status with progress bar (pause / resume / cancel)
- Axis movement controls (X/Y/Z) with adjustable step size
- Fan speed & print speed control
- Custom GCode input
- Collapsible connection settings (accordion)
- **Portrait:** scrollable single column
- **Landscape:** fixed 2-column layout, fits one screen without scrolling
- Connection settings saved in browser `localStorage`

## Requirements

- Klipper + Moonraker running on your printer's board (e.g. BTT CB1, Raspberry Pi)
- Python 3 on the board (pre-installed on most Klipper images)
- Git (for installation)

## Installation

SSH into your board, then:

```bash
git clone https://github.com/YOUR_USERNAME/simple3D.git ~/simple3D
cd ~/simple3D
chmod +x install_service.sh
./install_service.sh
```

The service will start automatically and will run on every boot.

Access the UI from any browser on your local network:

```
http://<your-board-ip>:8080
```

## First Run

1. Open `http://<board-ip>:8080` in your browser
2. Click the **Connection** header to expand settings (if collapsed)
3. Enter your Moonraker IP (usually the same as the board IP) and port (default: `7125`)
4. Click **Save & Connect**

Settings are saved in the browser — you only need to enter them once.

## Updating

```bash
cd ~/simple3D
git pull
```

No service restart needed — files are served statically.

## Service Management

```bash
# Check status
sudo systemctl status simple3d

# Restart
sudo systemctl restart simple3d

# Stop
sudo systemctl stop simple3d

# Disable autostart
sudo systemctl disable simple3d
```

## Manual Run (without service)

```bash
cd ~/simple3D
python3 -m http.server 8080
```

## File Structure

```
simple3D/
├── index.html          # entire application (single file)
├── simple3d.service    # systemd service definition
├── install_service.sh  # installer script
└── README.md
```

## Compatibility

Tested on:
- iOS 10 Safari (target device)
- Modern browsers (Chrome, Firefox, Safari)

The UI uses ES5 JavaScript and `-webkit-` CSS prefixes for maximum browser compatibility.

## License

MIT
