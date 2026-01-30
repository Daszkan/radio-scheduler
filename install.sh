#!/bin/bash

# Determine the directory where the script is located (assuming it's the app directory)
APP_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" &> /dev/null && pwd )"

echo "--- RadioScheduler Installation ---"

# 0. Check for MPD (Warning only)
if ! command -v mpd &> /dev/null; then
    echo "WARNING: MPD (Music Player Daemon) was not found!"
    echo "This application requires MPD and MPC to function."
    echo "Please install them using your package manager (e.g., sudo apt install mpd mpc)."
    echo "---------------------------------------------------"
fi

# 1. Check and install dependencies
#echo "[1/3] Installing Python dependencies..."
#if command -v pip3 &> /dev/null; then
#    pip3 install -r "$APP_DIR/requirements.txt"
#else
#    echo "Error: pip3 not found. Please install python3-pip."
#    exit 1
#fi

# Nadanie praw wykonywania
chmod +x "$APP_DIR/radio-scheduler-gui"
chmod +x "$APP_DIR/radio-scheduler"

# 2. Prepare .desktop file
ICON_PATH="$APP_DIR/app_icon.png"
# Use full path to python3 and script
PYTHON_EXEC=$(which python3)
EXEC_CMD="$PYTHON_EXEC \"$APP_DIR/radio-scheduler-gui.py\""

DESKTOP_CONTENT="[Desktop Entry]
Name=RadioScheduler
Comment=Radio station scheduler and player
Exec=$EXEC_CMD
Icon=$ICON_PATH
Terminal=false
Type=Application
Categories=AudioVideo;Audio;Player;
StartupNotify=true"

# 3. Create shortcuts
echo "[2/3] Creating application menu shortcut..."

mkdir -p "$HOME/.local/share/applications"

cat > "$HOME/.local/share/applications/radio-scheduler.desktop" << 'EOF'
[Desktop Entry]
Name=Radio Scheduler
GenericName=Planer stacji radiowych
Comment=Scheduling and automatic playback of Internet radio stations
Exec=/usr/bin/radio-scheduler-gui
Icon=radio-scheduler
Terminal=false
Type=Application
Categories=Audio;Player;Utility;
StartupNotify=true
EOF

chmod 644 "$HOME/.local/share/applications/radio-scheduler.desktop"

update-desktop-database "$HOME/.local/share/applications/" 2>/dev/null || true

echo "[3/3] Menu entry created."

echo "--- Installation completed successfully! ---"
echo "You can now launch the application from the menu or desktop."
