@echo off
pip install -r "%~dp0requirements.txt" >nul 2>&1
start "" pythonw "%~dp0bluetooth_battery_tray.py"
