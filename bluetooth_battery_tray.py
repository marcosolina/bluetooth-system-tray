"""
Bluetooth Battery System Tray Application for Windows 11
Displays battery percentage of connected Bluetooth devices in the system tray.
"""

import subprocess
import threading
import time
import re
import sys
import os
import winreg
from PIL import Image, ImageDraw, ImageFont
import pystray


APP_NAME = "BluetoothBattery"
REGISTRY_PATH = r"Software\Microsoft\Windows\CurrentVersion\Run"


def get_executable_path():
    """Get the path to the current executable or script."""
    if getattr(sys, 'frozen', False):
        # Running as compiled exe
        return sys.executable
    else:
        # Running as script - use pythonw to run without console
        return f'pythonw "{os.path.abspath(__file__)}"'


def is_autostart_enabled():
    """Check if autostart is enabled in Windows registry."""
    try:
        key = winreg.OpenKey(winreg.HKEY_CURRENT_USER, REGISTRY_PATH, 0, winreg.KEY_READ)
        try:
            winreg.QueryValueEx(key, APP_NAME)
            return True
        except FileNotFoundError:
            return False
        finally:
            winreg.CloseKey(key)
    except WindowsError:
        return False


def set_autostart(enabled):
    """Enable or disable autostart in Windows registry."""
    try:
        key = winreg.OpenKey(winreg.HKEY_CURRENT_USER, REGISTRY_PATH, 0, winreg.KEY_SET_VALUE)
        if enabled:
            winreg.SetValueEx(key, APP_NAME, 0, winreg.REG_SZ, get_executable_path())
        else:
            try:
                winreg.DeleteValue(key, APP_NAME)
            except FileNotFoundError:
                pass
        winreg.CloseKey(key)
        return True
    except WindowsError:
        return False


def get_bluetooth_devices_battery():
    """
    Get battery levels using PowerShell and PnP device properties.
    Checks multiple device classes to find all Bluetooth devices with battery info.
    """
    devices = []
    seen_names = set()

    # PowerShell script to check multiple device types (only currently connected devices)
    # Connected devices have empty LastConnectedTime, disconnected ones have a past timestamp
    ps_script = '''
# Check Bluetooth class
Get-PnpDevice -Class Bluetooth -Status OK -ErrorAction SilentlyContinue | ForEach-Object {
    $device = $_
    $battery = Get-PnpDeviceProperty -InstanceId $device.InstanceId -KeyName '{104EA319-6EE2-4701-BD47-8DDBF425BBE5} 2' -ErrorAction SilentlyContinue
    $lastConn = Get-PnpDeviceProperty -InstanceId $device.InstanceId -KeyName 'DEVPKEY_Bluetooth_LastConnectedTime' -ErrorAction SilentlyContinue
    if ($battery.Data -ne $null -and $lastConn.Data -eq $null) {
        Write-Output "DEVICE:$($device.FriendlyName)|BATTERY:$($battery.Data)"
    }
}

# Check BTHENUM devices (classic Bluetooth)
Get-PnpDevice -Status OK -ErrorAction SilentlyContinue | Where-Object { $_.InstanceId -like 'BTHENUM*' } | ForEach-Object {
    $device = $_
    $battery = Get-PnpDeviceProperty -InstanceId $device.InstanceId -KeyName '{104EA319-6EE2-4701-BD47-8DDBF425BBE5} 2' -ErrorAction SilentlyContinue
    $lastConn = Get-PnpDeviceProperty -InstanceId $device.InstanceId -KeyName 'DEVPKEY_Bluetooth_LastConnectedTime' -ErrorAction SilentlyContinue
    if ($battery.Data -ne $null -and $lastConn.Data -eq $null) {
        Write-Output "DEVICE:$($device.FriendlyName)|BATTERY:$($battery.Data)"
    }
}

# Check BTHLE devices (Bluetooth LE)
Get-PnpDevice -Status OK -ErrorAction SilentlyContinue | Where-Object { $_.InstanceId -like 'BTHLE*' } | ForEach-Object {
    $device = $_
    $battery = Get-PnpDeviceProperty -InstanceId $device.InstanceId -KeyName '{104EA319-6EE2-4701-BD47-8DDBF425BBE5} 2' -ErrorAction SilentlyContinue
    $lastConn = Get-PnpDeviceProperty -InstanceId $device.InstanceId -KeyName 'DEVPKEY_Bluetooth_LastConnectedTime' -ErrorAction SilentlyContinue
    if ($battery.Data -ne $null -and $lastConn.Data -eq $null) {
        Write-Output "DEVICE:$($device.FriendlyName)|BATTERY:$($battery.Data)"
    }
}
'''

    try:
        result = subprocess.run(
            ['powershell', '-NoProfile', '-ExecutionPolicy', 'Bypass', '-Command', ps_script],
            capture_output=True,
            text=True,
            timeout=30,
            creationflags=subprocess.CREATE_NO_WINDOW
        )

        if result.returncode == 0 and result.stdout.strip():
            for line in result.stdout.strip().split('\n'):
                line = line.strip()
                if line.startswith('DEVICE:') and '|BATTERY:' in line:
                    match = re.match(r'DEVICE:(.+)\|BATTERY:(\d+)', line)
                    if match:
                        name = match.group(1).strip()
                        battery = int(match.group(2))

                        # Skip duplicates
                        if name not in seen_names:
                            devices.append({
                                'name': name,
                                'battery': battery
                            })
                            seen_names.add(name)

    except (subprocess.TimeoutExpired, subprocess.SubprocessError, FileNotFoundError) as e:
        print(f"Error running PowerShell: {e}")

    return devices


def create_battery_icon(percentage, size=64):
    """
    Create a battery icon image with the percentage displayed.
    """
    image = Image.new('RGBA', (size, size), (0, 0, 0, 0))
    draw = ImageDraw.Draw(image)

    # Determine color based on battery level
    if percentage is None:
        color = (128, 128, 128)  # Gray for unknown
        text = "?"
    elif percentage <= 20:
        color = (255, 80, 80)  # Red for low battery
        text = str(percentage)
    elif percentage <= 50:
        color = (255, 200, 80)  # Yellow/Orange for medium
        text = str(percentage)
    else:
        color = (80, 200, 80)  # Green for good battery
        text = str(percentage)

    # Draw battery outline
    margin = 4
    battery_width = size - margin * 2 - 6
    battery_height = size - margin * 2
    battery_x = margin
    battery_y = margin

    # Main battery body
    draw.rectangle(
        [battery_x, battery_y, battery_x + battery_width, battery_y + battery_height],
        outline=(255, 255, 255),
        width=2
    )

    # Battery terminal
    terminal_width = 12
    terminal_height = 6
    terminal_x = battery_x + (battery_width - terminal_width) // 2
    draw.rectangle(
        [terminal_x, battery_y - terminal_height + 2, terminal_x + terminal_width, battery_y + 2],
        fill=(255, 255, 255)
    )

    # Fill based on percentage
    if percentage is not None:
        fill_height = int((battery_height - 6) * (percentage / 100))
        fill_y = battery_y + battery_height - 3 - fill_height
        draw.rectangle(
            [battery_x + 3, fill_y, battery_x + battery_width - 3, battery_y + battery_height - 3],
            fill=color
        )

    # Draw percentage text - larger font
    font_size = 28 if len(text) <= 2 else 22
    try:
        font = ImageFont.truetype("arialbd.ttf", font_size)  # Bold Arial
    except (OSError, IOError):
        try:
            font = ImageFont.truetype("arial.ttf", font_size)
        except (OSError, IOError):
            font = ImageFont.load_default()

    bbox = draw.textbbox((0, 0), text, font=font)
    text_width = bbox[2] - bbox[0]
    text_height = bbox[3] - bbox[1]
    text_x = (size - text_width) // 2
    text_y = (size - text_height) // 2

    # Text outline for visibility
    for dx, dy in [(-1, -1), (-1, 1), (1, -1), (1, 1), (-1, 0), (1, 0), (0, -1), (0, 1)]:
        draw.text((text_x + dx, text_y + dy), text, fill=(0, 0, 0), font=font)
    draw.text((text_x, text_y), text, fill=(255, 255, 255), font=font)

    return image


class BluetoothBatteryTray:
    def __init__(self, update_interval=60):
        self.update_interval = update_interval
        self.running = True
        self.icon = None
        self.devices = []

    def get_clean_name(self, name):
        """Clean up device name for display."""
        name = name.replace(" Hands-Free AG", "")
        name = name.replace(" Avrcp Transport", "")
        return name

    def get_tooltip(self):
        """Generate tooltip text with all device battery info."""
        if not self.devices:
            return "Bluetooth Battery\nNo devices found"

        lines = ["Bluetooth Battery"]
        for device in self.devices:
            battery = device['battery']
            name = self.get_clean_name(device['name'])
            lines.append(f"{battery:3d}% - {name}")
        return "\n".join(lines)

    def get_lowest_battery(self):
        """Get the lowest battery percentage among all devices."""
        if self.devices:
            return min(device["battery"] for device in self.devices)
        return None

    def update_devices(self):
        """Update the list of devices and refresh the icon."""
        self.devices = get_bluetooth_devices_battery()
        if self.icon:
            battery = self.get_lowest_battery()
            self.icon.icon = create_battery_icon(battery)
            self.icon.title = self.get_tooltip()
            # Update menu to reflect current devices
            self.icon.menu = self.create_menu()

    def update_loop(self):
        """Background thread that periodically updates device info."""
        while self.running:
            self.update_devices()
            time.sleep(self.update_interval)

    def on_quit(self, icon, item):
        """Handle quit menu action."""
        self.running = False
        icon.stop()

    def on_refresh(self, icon, item):
        """Handle refresh menu action."""
        self.update_devices()

    def on_toggle_autostart(self, icon, item):
        """Toggle autostart setting."""
        current = is_autostart_enabled()
        set_autostart(not current)

    def create_menu(self):
        """Create the system tray context menu."""
        items = [
            pystray.MenuItem("Bluetooth Battery", None, enabled=False),
            pystray.Menu.SEPARATOR,
            pystray.MenuItem("Refresh", self.on_refresh),
            pystray.Menu.SEPARATOR
        ]

        if self.devices:
            for device in self.devices:
                name = self.get_clean_name(device['name'])
                battery = device['battery']
                items.append(
                    pystray.MenuItem(
                        f"{battery:3d}% - {name}",
                        None,
                        enabled=False
                    )
                )
        else:
            items.append(
                pystray.MenuItem(
                    "No devices found",
                    None,
                    enabled=False
                )
            )

        items.append(pystray.Menu.SEPARATOR)
        items.append(
            pystray.MenuItem(
                "Start with Windows",
                self.on_toggle_autostart,
                checked=lambda item: is_autostart_enabled()
            )
        )
        items.append(pystray.Menu.SEPARATOR)
        items.append(pystray.MenuItem("Quit", self.on_quit))

        return pystray.Menu(*items)

    def run(self):
        """Start the system tray application."""
        # Initial device scan
        self.update_devices()

        # Create the icon
        battery = self.get_lowest_battery()
        self.icon = pystray.Icon(
            "bluetooth_battery",
            create_battery_icon(battery),
            self.get_tooltip(),
            menu=self.create_menu()
        )

        # Start update thread
        update_thread = threading.Thread(target=self.update_loop, daemon=True)
        update_thread.start()

        # Run the icon (this blocks)
        self.icon.run()


def main():
    print("Starting Bluetooth Battery Monitor...")
    print("The app will appear in your system tray.")
    print()

    # Show initial device scan
    devices = get_bluetooth_devices_battery()
    if devices:
        print("Found devices:")
        for device in devices:
            print(f"  - {device['name']}: {device['battery']}%")
    else:
        print("No Bluetooth devices with battery info found.")
        print("Make sure your Bluetooth device is connected.")

    print()
    print("Right-click the tray icon to see options or quit.")

    # Start the tray app
    app = BluetoothBatteryTray(update_interval=60)
    app.run()


if __name__ == "__main__":
    main()
