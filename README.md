# RadioScheduler

RadioScheduler is a desktop application for scheduling and automatically playing internet radio stations. It consists of a background daemon and a graphical user interface (GUI) for management.


## Main Features

*   **Graphical User Interface**: Intuitive management of stations, schedules, and settings.
*   **Background Daemon**: Ensures uninterrupted playback according to the schedule, even after the GUI is closed.
*   **Advanced Scheduling**: Define playback rules for specific days of the week and time ranges.
*   **News Breaks**: Automatically switch to a news station at specified times.
*   **System Tray Integration**: Quick access to favorite stations, volume control, and playback status.
*   **Sleep Timer**: Automatically stop playback after a specified duration.
*   **Playlist Import**: Import stations from M3U/PLS files.
*   **Connection Testing**: Verify station URLs directly within the editor.
*   **Auto-resume**: Automatically return to the schedule after a manual override period.
*   **Full Backup**: Create a ZIP archive containing configuration and logs.
*   **Multi-language Support**: The interface is available in Polish and English.
*   **Customization**: Ability to edit keyboard shortcuts.
*   **Configuration Import and Export**: Easily back up and transfer settings.

## Requirements

*   **Python 3.8+**
*   Python libraries: `PySide6`, `PyYAML`
*   **Music Player Daemon (MPD)** and `mpc` (command-line client)

## Installation
**Arch Linux / Manjaro / EndeavourOS (recommended – AUR)**
```bash
yay -S radio-scheduler-git
# or
paru -S radio-scheduler-git
```
After installation the menu entry should appear automatically.
Launch with: radio-scheduler-gui


**Manual installation (from source)**
1.  **Clone the repository:**
    ```bash
    git clone https://github.com/Daszkan/radio-scheduler.git
    cd radio-scheduler
    ```

2.  **Install Python dependencies:**
    ```bash
    pip install -r requirements.txt
    ```

3.  **Install MPD and MPC:**

    *   **Debian / Ubuntu:**
        ```bash
        sudo apt update && sudo apt install mpd mpc
        ```
    *   **Arch Linux:**
        ```bash
        sudo pacman -Syu mpd mpc
        ```
    *   **Fedora:**
        ```bash
        sudo dnf install mpd mpc
        ```

4.  **Run the installation script (Optional):**
    This script installs Python dependencies and creates desktop shortcuts.
    ```bash
    chmod +x install.sh
    ./install.sh
    ```

5.  **Configure MPD:**
    Ensure you have a basic MPD configuration in your home directory, e.g., at `~/.config/mpd/mpd.conf`. The application has a built-in editor for this file. MPD must be running for the application to work correctly.
    ```bash
    mpd
    ```

## Usage

To launch the graphical interface, run the following command in the main project directory:

```bash
python radio-scheduler-gui.py
```

The scheduler daemon (`radio-scheduler.py`) will start automatically in the background when the GUI is first launched.

## Configuration

All application settings, including the station list and schedule, are stored in the `~/.config/radio-scheduler/config.yaml` file. This file is created and managed automatically by the graphical interface.

## License
This project is licensed under the MIT License. See the LICENSE file for more information.
