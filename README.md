# RadioScheduler

RadioScheduler is a desktop application for scheduling and automatically playing internet radio stations. It consists of a background daemon and a graphical user interface (GUI) for management.


## Main Features

*   **Graphical User Interface**: Intuitive management of stations, schedules, and settings.
*   **Background Daemon**: Ensures uninterrupted playback according to the schedule, even after the GUI is closed.
*   **Advanced Scheduling**: Define playback rules for specific days of the week and time ranges.
*   **News Breaks**: Automatically switch to a news station at specified times.
*   **System Tray Integration**: Quick access to favorite stations, volume control, and playback status.
*   **Multi-language Support**: The interface is available in Polish and English.
*   **Customization**: Ability to edit keyboard shortcuts.
*   **Configuration Import and Export**: Easily back up and transfer settings.

## Requirements

*   **Python 3.8+**
*   Python libraries: `PySide6`, `PyYAML`
*   **Music Player Daemon (MPD)** and `mpc` (command-line client)

## Installation

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

4.  **Configure MPD:**
    Ensure you have a basic MPD configuration in your home directory, e.g., at `~/.config/mpd/mpd.conf`. The application has a built-in editor for this file. MPD must be running for the application to work correctly.
    ```bash
    mpd
    ```

## Usage

To launch the graphical interface, run the following command in the main project directory:

```bash
python radio-scheduler-gui.py
```

Demon harmonogramu (`radio-scheduler.py`) zostanie uruchomiony automatycznie w tle przy pierwszym starcie GUI.

## Konfiguracja

Wszystkie ustawienia aplikacji, w tym lista stacji i harmonogram, są przechowywane w pliku `~/.config/radio-scheduler/config.yaml`. Plik ten jest tworzony i zarządzany automatycznie przez interfejs graficzny.

## Licencja

Ten projekt jest udostępniany na licencji MIT. Zobacz plik LICENSE, aby uzyskać więcej informacji.
