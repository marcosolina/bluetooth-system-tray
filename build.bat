@echo off
echo Installing dependencies...
pip install -r requirements.txt
pip install pyinstaller

echo.
echo Building executable...
python -m PyInstaller --onefile --noconsole --name "BluetoothBattery" bluetooth_battery_tray.py

echo.
echo Done! Executable is at: dist\BluetoothBattery.exe
pause
