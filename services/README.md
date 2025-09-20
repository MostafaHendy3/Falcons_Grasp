# Game Services

This directory contains systemd service files for running the game scripts as Linux services.

## Service Files

1. **falcongrasp.service** - Service for `FalconGrasp_Complet_Sound.py`
2. **pycatch.service** - Service for `pyCatch1_2025.py`

## Installation Instructions

### Prerequisites
- Ensure Python 3 is installed on the target system
- Install required Python packages (PyQt5, OpenCV, paho-mqtt, requests, numpy, etc.)
- Update the paths in the service files if they differ on your target system

### Install Services

1. Copy service files to systemd directory:
```bash
sudo cp falcongrasp.service /etc/systemd/system/
sudo cp pycatch.service /etc/systemd/system/
```

2. Reload systemd to recognize new services:
```bash
sudo systemctl daemon-reload
```

3. Enable services to start on boot (optional):
```bash
sudo systemctl enable falcongrasp.service
sudo systemctl enable pycatch.service
```

### Service Management

#### Start services:
```bash
sudo systemctl start falcongrasp.service
sudo systemctl start pycatch.service
```

#### Stop services:
```bash
sudo systemctl stop falcongrasp.service
sudo systemctl stop pycatch.service
```

#### Check service status:
```bash
sudo systemctl status falcongrasp.service
sudo systemctl status pycatch.service
```

#### View service logs:
```bash
sudo journalctl -u falcongrasp.service -f
sudo journalctl -u pycatch.service -f
```

### Configuration Notes

- **User/Group**: Both services run as user `mostafa`. Update this in the service files if needed.
- **Working Directory**: Services use the game2 directory structure. Update paths if deploying elsewhere.
- **Python Path**: Services use `/usr/local/bin/python3`. Update if Python is installed elsewhere.
- **Display**: FalconGrasp service includes GUI environment variables for X11 display.
- **Resources**: Memory and CPU limits are set for system stability.

### Troubleshooting

- Check service logs with `journalctl` if services fail to start
- Ensure all Python dependencies are installed
- Verify file paths match your deployment structure
- For GUI applications, ensure X11 forwarding or local display is available
