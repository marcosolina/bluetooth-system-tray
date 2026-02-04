# Bluetooth Battery Tray

A Windows 11 system tray application that displays the battery percentage of connected Bluetooth devices.

## Features

- Shows battery level of all connected Bluetooth devices in the system tray
- Icon displays the lowest battery percentage among all devices
- Color-coded icon: green (>50%), yellow (21-50%), red (≤20%)
- Tooltip shows all devices with their battery levels
- Right-click menu for quick access to device info
- Auto-refreshes every 60 seconds
- Manual refresh option

## Requirements

- Windows 11
- Python 3.8+
- Connected Bluetooth devices that report battery level

## Installation

1. Install dependencies:
   ```
   pip install -r requirements.txt
   ```

## Usage

### Option 1: Run the executable
Build the exe (see below) and run `BluetoothBattery.exe` from the `dist` folder.

### Option 2: Double-click run.bat
The app starts silently in the system tray. The console window closes automatically.

### Option 3: Run from command line
```
python bluetooth_battery_tray.py
```

## Building the Executable

To create a standalone exe file:

1. Run `build.bat`, or manually:
   ```
   pip install pyinstaller
   python -m PyInstaller --onefile --noconsole --name "BluetoothBattery" bluetooth_battery_tray.py
   ```

2. The executable will be created at `dist\BluetoothBattery.exe`

## System Tray

- **Hover** over the icon to see all devices and battery levels
- **Right-click** to open the menu:
  - View all devices with battery percentages
  - Refresh to update battery levels
  - Quit to exit the application

## Supported Devices

Works with Bluetooth devices that report battery level to Windows, including:
- Bluetooth headphones
- Wireless controllers
- Bluetooth keyboards/mice
