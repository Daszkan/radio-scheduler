#!/usr/bin/env bash

# RadioScheduler - Manual Installation Script
# Run this from the cloned repository directory

set -euo pipefail

# Determine the directory where the script is located
APP_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" &> /dev/null && pwd )"

echo "=== RadioScheduler Installation ==="
echo "This script should be run from the cloned repository directory."
echo "Current directory: $APP_DIR"
echo ""

# 0. Check for required tools
echo "[1/4] Checking dependencies..."

if ! command -v mpd &> /dev/null; then
    echo "WARNING: MPD (Music Player Daemon) not found!"
    echo "This application requires MPD and MPC to function."
    echo "Please install them using your package manager:"
    echo "  Arch:     sudo pacman -S mpd mpc"
    echo "  Debian/Ubuntu: sudo apt install mpd mpc"
    echo "  Fedora:   sudo dnf install mpd mpc"
    echo ""
fi

if ! command -v python3 &> /dev/null; then
    echo "ERROR: python3 not found. Please install Python 3."
    exit 1
fi

if ! command -v pip3 &> /dev/null; then
    echo "ERROR: pip3 not found. Please install python-pip."
    exit 1
fi

# 1. Install Python dependencies (only in virtualenv or user mode recommended)
echo "[2/4] Installing Python dependencies..."

echo "Note: Installing packages system-wide can break your system."
echo "Recommended: use a virtual environment or --user flag."

read -p "Continue with pip install --user? [y/N] " -n 1 -r
echo
if [[ $REPLY =~ ^[Yy]$ ]]; then
    pip3 install --user -r "$APP_DIR/requirements.txt"
else
    echo "Skipping pip install. Make sure dependencies are installed manually."
fi

# 2. Make scripts executable
echo "[3/4] Making scripts executable..."
chmod +x "$APP_DIR/radio-scheduler-gui.py"
chmod +x "$APP_DIR/radio-scheduler.py"

# 3. Create .desktop file
echo "[4/4] Creating application menu entry..."

ICON_PATH="$APP_DIR/app_icon.png"
EXEC_CMD="$APP_DIR/radio-scheduler-gui.py"

# Use absolute path for Exec
cat > "$HOME/.local/share/applications/radio-scheduler.desktop" << EOF
[Desktop Entry]
Name=Radio Scheduler
GenericName=Internet Radio Scheduler
Comment=Automatic scheduling and playback of internet radio stations
Exec=python3 $EXEC_CMD
Icon=$ICON_PATH
Terminal=false
Type=Application
Categories=Audio;Player;Utility;
StartupNotify=true
EOF

chmod 644 "$HOME/.local/share/applications/radio-scheduler.desktop"

# Refresh menu
update-desktop-database "$HOME/.local/share/applications/" 2>/dev/null || true

echo ""
echo "=== Installation completed ==="
echo "Menu entry created at: ~/.local/share/applications/radio-scheduler.desktop"
echo "You can now launch the application from your menu."
echo ""
echo "To run manually:"
echo "  python3 $APP_DIR/radio-scheduler-gui.py"
echo ""
echo "Have fun with RadioScheduler!"