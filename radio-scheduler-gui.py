#!/usr/bin/env python3
# Copyright (c) 2025 Daszkan (Jacek S.)
#
# This software is released under the MIT License.
# https://opensource.org/licenses/MIT
import sys
import yaml
import subprocess
from pathlib import Path
from datetime import time
from collections import defaultdict
import logging, os

from translations import TEXTS # type: ignore
import PySide6
from mpc_controller import MPCController # type: ignore
from PySide6.QtWidgets import (
    QAbstractItemView,
    QApplication,
    QCheckBox,
    QComboBox,
    QDialog,
    QDialogButtonBox,
    QFileDialog,
    QFormLayout,
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QListWidget,
    QListWidgetItem,
    QMainWindow,
    QMenu,
    QMessageBox,
    QPushButton,
    QRadioButton,
    QSlider,
    QSpinBox,
    QStyle,
    QSystemTrayIcon,
    QTabWidget,
    QTableWidget,
    QTableWidgetItem,
    QTextEdit,
    QTimeEdit,
    QWidget,
    QVBoxLayout,
    QTreeWidget,
    QTreeWidgetItem,
    QTreeWidgetItemIterator,
    QSpacerItem,
    QSizePolicy
)
from PySide6.QtCore import QEvent, Qt, QTimer
from PySide6.QtGui import QAction, QDesktopServices, QIcon, QFont, QKeySequence, QShortcut

# --- Global Paths and Configuration ---
CONFIG_PATH = Path.home() / ".config/radio-scheduler/config.yaml"
LOG_PATH = Path.home() / ".config/radio-scheduler/radio-scheduler-gui.log"
DAEMON_PATH = Path.home() / ".config/radio-scheduler/radio-scheduler.py"
MANUAL_OVERRIDE_LOCK = Path.home() / ".config/radio-scheduler/manual_override.lock"
ICON_PATH = Path(__file__).parent / "app_icon.png"

logging.basicConfig(
    filename=LOG_PATH,
    level=logging.ERROR,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
DEFAULT_ICON = QStyle.StandardPixmap.SP_MediaPlay # Corrected enum usage
MANUAL_ICON = QStyle.StandardPixmap.SP_MediaSeekForward # Corrected enum usage

mpc = MPCController()

def ensure_daemon():
    if subprocess.call(["pgrep", "-f", "radio-scheduler.py"], stdout=subprocess.DEVNULL) != 0:
        subprocess.Popen([sys.executable, str(DAEMON_PATH)], start_new_session=True)

def clear_and_exit():
    mpc.clear()
    mpc.stop()
    subprocess.run(["pkill", "-f", "radio-scheduler.py"], check=False)
    QApplication.quit()

def play_now(station):
    try:
        MANUAL_OVERRIDE_LOCK.touch()
        if not mpc.play_url(station["url"]):
            raise Exception("MPC command failed, check mpc_controller.log")
    except (subprocess.CalledProcessError, FileNotFoundError) as e:
        logging.error(f"Błąd podczas ręcznego odtwarzania stacji {station.get('name', '')}: {e}")
        # This function is called from outside MainWindow, so we can't use self.translator
        # A simple message box is sufficient.
        QMessageBox.critical(None, "Playback Error", f"Could not play station. Check logs:\n{LOG_PATH}")

class Translator:
    def __init__(self, lang='pl'):
        self.lang = lang
        # Fallback to English if a key is missing in the selected language, then to the key itself.
        self.texts = defaultdict(lambda: TEXTS['en'][key], TEXTS.get(lang, TEXTS['pl'])) # type: ignore

    def tr(self, key, **kwargs):
        text = self.texts.get(key, key)
        return text.format(**kwargs)

class TimeRangeEditor(QDialog):
    def __init__(self, rule=None, tree=None, parent=None, is_news_rule=False): # Added parent for consistency
        super().__init__(parent)
        self.translator = parent.translator
        self.setWindowTitle(self.translator.tr("edit_interval"))
        self.setModal(True)
        layout = QFormLayout(self)

        self.days = QComboBox()
        # Add items with associated data to make it more robust
        self.day_map_data = {
            "days_workdays": ["mon", "tue", "wed", "thu", "fri"], "days_weekend": ["sat", "sun"],
            "days_everyday": ["mon", "tue", "wed", "thu", "fri", "sat", "sun"],
            "day_mon": ["mon"], "day_tue": ["tue"], "day_wed": ["wed"], "day_thu": ["thu"],
            "day_fri": ["fri"], "day_sat": ["sat"], "day_sun": ["sun"]
        }
        for key, data in self.day_map_data.items():
            self.days.addItem(self.translator.tr(key), data)

        self.from_time = QTimeEdit()
        self.from_time.setDisplayFormat("HH:mm")
        self.to_time = QTimeEdit()
        self.to_time.setDisplayFormat("HH:mm")
        self.is_news_rule = is_news_rule

        self.station = QComboBox()
        if tree:
            for i in range(tree.topLevelItemCount()):
                parent = tree.topLevelItem(i)
                genre = parent.text(0)
                for j in range(parent.childCount()):
                    child = parent.child(j)
                    name = child.text(0).lstrip("★ ").strip()
                    self.station.addItem(f"{genre} → {name}", name)

        if self.is_news_rule:
            self.interval = QSpinBox(minimum=15, maximum=120, singleStep=15)
            self.duration = QSpinBox(minimum=1, maximum=15)
            layout.addRow(self.translator.tr("interval_minutes"), self.interval)
            layout.addRow(self.translator.tr("duration_minutes"), self.duration)


        if rule:
            days = rule.get("days", [])
            # Find the index corresponding to the list of days
            for i in range(self.days.count()):
                if self.days.itemData(i) == days:
                    self.days.setCurrentIndex(i)
                    break
            self.from_time.setTime(time.fromisoformat(rule["from"])) # Time from config
            self.to_time.setTime(time.fromisoformat(rule["to"])) # Time from config
            idx = self.station.findData(rule["station"])
            if idx >= 0: self.station.setCurrentIndex(idx)
            if self.is_news_rule:
                self.interval.setValue(rule.get("interval_minutes", 60))
                self.duration.setValue(rule.get("duration_minutes", 8))

        layout.addRow(self.translator.tr("days"), self.days)
        layout.addRow(self.translator.tr("from"), self.from_time)
        layout.addRow(self.translator.tr("to"), self.to_time)
        layout.addRow(self.translator.tr("station"), self.station)

        btns = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        btns.accepted.connect(self.accept)
        btns.rejected.connect(self.reject)
        layout.addRow(btns)

    def get_rule(self):
        if self.exec() != QDialog.Accepted: return None
        result = {
            "days": self.days.currentData(),
            "from": self.from_time.time().toString("HH:mm"),
            "to": self.to_time.time().toString("HH:mm"),
            "station": self.station.currentData()
        }
        if self.is_news_rule:
            result.update({
                "interval_minutes": self.interval.value(),
                "duration_minutes": self.duration.value()
            })
        return result

class AboutTab(QWidget):
    """'About' tab showing application info, MPD status, and environment details."""
    def __init__(self, parent=None): # Added parent for consistency
        super().__init__()
        self.translator = parent.translator if parent else None
        self.init_ui()
        self.retranslate_ui()
    
    def init_ui(self):
        """Initializes the static UI components of the tab."""
        main_layout = QVBoxLayout(self)
        main_layout.setAlignment(Qt.AlignTop)

        # --- Top Header ---
        header_layout = QHBoxLayout()
        icon_label = QLabel()
        if ICON_PATH.exists():
            icon_label.setPixmap(QIcon(str(ICON_PATH)).pixmap(64, 64))
        header_layout.addWidget(icon_label)

        title_layout = QVBoxLayout()
        self.app_name_label = QLabel("RadioScheduler v1.0")
        self.app_name_label.setFont(QFont("Arial", 20, QFont.Bold))
        title_layout.addWidget(self.app_name_label)
        header_layout.addLayout(title_layout)
        header_layout.addStretch()
        main_layout.addLayout(header_layout)

        # --- Info Section ---
        info_group = QGroupBox()
        info_layout = QFormLayout(info_group)
        self.author_label = QLabel("Daszkan (Jacek S.)")
        self.license_label = QLabel("MIT License")
        self.github_label = QLabel('<a href="https://github.com/Daszkan/radio-scheduler">github.com/Daszkan/radio-scheduler</a>')
        self.github_label.setOpenExternalLinks(True)
        info_layout.addRow(self.translator.tr("author"), self.author_label)
        info_layout.addRow(self.translator.tr("license"), self.license_label)
        info_layout.addRow("GitHub:", self.github_label)
        main_layout.addWidget(info_group)

        # --- MPD Status ---
        mpd_group = QGroupBox(self.translator.tr("mpd_status"))
        mpd_layout = QHBoxLayout(mpd_group)
        self.mpd_status_icon = QLabel()
        self.mpd_status_label = QLabel()
        mpd_layout.addWidget(self.mpd_status_icon)
        mpd_layout.addWidget(self.mpd_status_label)
        mpd_layout.addStretch()
        main_layout.addWidget(mpd_group)

        # --- MPD Stats ---
        self.stats_group = QGroupBox(self.translator.tr("mpd_stats_title"))
        stats_layout = QFormLayout(self.stats_group)
        self.mpd_version_label = QLabel()
        self.mpd_uptime_label = QLabel()
        stats_layout.addRow(self.translator.tr("mpd_version"), self.mpd_version_label)
        stats_layout.addRow(self.translator.tr("mpd_uptime"), self.mpd_uptime_label)
        main_layout.addWidget(self.stats_group)

        # --- Application Paths ---
        paths_group = QGroupBox(self.translator.tr("app_paths_title"))
        paths_layout = QFormLayout(paths_group)
        
        config_path_layout = self.create_path_widget(CONFIG_PATH)
        log_path_layout = self.create_path_widget(LOG_PATH)

        paths_layout.addRow(self.translator.tr("config_file_path"), config_path_layout)
        paths_layout.addRow(self.translator.tr("log_file_path"), log_path_layout)
        main_layout.addWidget(paths_group)

        # --- Environment Info ---
        env_group = QGroupBox(self.translator.tr("env_info_title"))
        env_layout = QFormLayout(env_group)
        python_version_label = QLabel(f"{sys.version.split(' ')[0]}")
        pyside_version_label = QLabel(f"{PySide6.__version__}")
        env_layout.addRow(self.translator.tr("python_version"), python_version_label)
        env_layout.addRow(self.translator.tr("pyside_version"), pyside_version_label)
        main_layout.addWidget(env_group)

        # --- Instructions ---
        self.instr_group = QGroupBox(self.translator.tr("mpd_install_title"))
        self.instr_group.setCheckable(True)
        self.instr_group.setChecked(False)
        instr_layout = QVBoxLayout(self.instr_group)
        
        instr_text = QTextEdit()
        instr_text.setReadOnly(True)
        instr_text.setHtml(f"""
            <p>{self.translator.tr("mpd_intro")}</p>
            <ol>
                <li><b>Debian/Ubuntu:</b><br><pre>sudo apt update && sudo apt install mpd mpc</pre></li>
                <li><b>Arch Linux:</b><br><pre>sudo pacman -Syu mpd mpc</pre></li>
                <li><b>Fedora:</b><br><pre>sudo dnf install mpd mpc</pre></li>
                <li><b>{self.translator.tr("mpd_config_user")}</b><br>{self.translator.tr("mpd_config_details")}</li>
                <li><b>{self.translator.tr("mpd_run")}</b><br>{self.translator.tr("mpd_run_details")}</li>
            </ol>
            <p>{self.translator.tr("mpd_check")}</p>
        """)
        instr_layout.addWidget(instr_text)
        main_layout.addWidget(self.instr_group)

    def create_path_widget(self, path):
        layout = QHBoxLayout()
        line_edit = QLineEdit(str(path))
        line_edit.setReadOnly(True)
        button = QPushButton(self.translator.tr("open_dir"))
        button.clicked.connect(lambda: self.open_directory(path.parent))
        layout.addWidget(line_edit)
        layout.addWidget(button)
        return layout

    def open_directory(self, path):
        """Opens the specified directory in the default file manager."""
        QDesktopServices.openUrl(f"file:///{path}")

    def retranslate_ui(self):
        # This method is now only for text translation, not logic
        self.stats_group.setTitle(self.translator.tr("mpd_stats_title"))
        self.instr_group.setTitle(self.translator.tr("mpd_install_title"))
        # The content of the labels is set in update_content

    def update_content(self):
        """Fetches dynamic data (like MPD status) and updates the UI content."""
        is_mpd_running = subprocess.call(["pgrep", "-f", "mpd"], stdout=subprocess.DEVNULL) == 0
        if is_mpd_running:
            self.mpd_status_label.setText(self.translator.tr("mpd_status_active"))
            self.mpd_status_icon.setPixmap(self.style().standardIcon(QStyle.SP_DialogApplyButton).pixmap(16, 16))
            self.stats_group.setVisible(True)
            self.instr_group.setVisible(False) # Hide instructions if MPD is running

            try:
                # Use 'mpc version' as it's the most reliable way to get the version of a running daemon.
                mpc_version_res = subprocess.run(["mpc", "version"], capture_output=True, text=True, check=False)
                stats_res = subprocess.run(["mpc", "stats"], capture_output=True, text=True, check=False)

                self.mpd_version_label.setText(mpc_version_res.stdout.strip() if mpc_version_res.returncode == 0 else "N/A")

                if stats_res.returncode == 0:
                    uptime_line = next((line for line in stats_res.stdout.split('\n') if 'Uptime' in line), None)
                    self.mpd_uptime_label.setText(uptime_line.split(': ')[1] if uptime_line else 'N/A')
                else:
                    self.mpd_uptime_label.setText("N/A")

            except Exception as e:
                logging.error(f"Error updating 'About' tab content: {e}")
                self.stats_group.setVisible(False)
        else:
            self.mpd_status_label.setText(self.translator.tr("mpd_status_inactive"))
            self.mpd_status_icon.setPixmap(self.style().standardIcon(QStyle.SP_DialogCancelButton).pixmap(16, 16))
            self.stats_group.setVisible(False)
            self.instr_group.setVisible(True) # Show instructions if MPD is not running

class MainWindow(QMainWindow):
    """The main application window."""
    def __init__(self):
        super().__init__()
        self.last_known_song = None # Bufor dla aktualnie granego utworu
        self.is_restarting = False # Flaga do obsługi restartu
        self.resize(1100, 760)
        ensure_daemon()

        self.config = self.load_config()
        self.translator = Translator(self.config.get("language", "pl"))

        self.stations = self.config.get("stations", [])
        self.schedule = self.config.get("schedule", {})

        self.create_actions()
        self.create_tray_icon()

        # Timer do odświeżania
        self.timer = QTimer(self)
        self.timer.timeout.connect(self.on_timer_tick)
        self.timer.start(10000)

        self.tabs = QTabWidget()
        self.tab_stations_widget = self.tab_stations()
        self.tab_schedule_widget = self.tab_schedule()
        self.tab_news_widget = self.tab_news()
        self.about_tab = AboutTab(self)
        self.tab_settings_widget = self.tab_settings()
        self.tab_mpd_config_widget = self.tab_mpd_config()

        self.tabs.addTab(self.tab_stations_widget, "")
        self.tabs.addTab(self.tab_schedule_widget, "")
        self.tabs.addTab(self.tab_news_widget, "")
        self.tabs.addTab(self.tab_settings_widget, "")
        self.tabs.addTab(self.tab_mpd_config_widget, "")
        self.tabs.addTab(self.about_tab, "")

        self.setCentralWidget(self.tabs)
        self.retranslate_ui()

    def closeEvent(self, e):
        """Handles the window close event, showing a dialog to hide or exit."""
        if self.is_restarting:
            e.accept()
            return
        msg_box = QMessageBox(self) # Message box for close event
        msg_box.setWindowTitle(self.translator.tr("app_title"))
        msg_box.setText(self.translator.tr("close_prompt_title"))
        msg_box.setInformativeText(self.translator.tr("close_prompt_text"))
        
        hide_button = msg_box.addButton(self.translator.tr("hide"), QMessageBox.ActionRole)
        exit_button = msg_box.addButton(self.translator.tr("exit"), QMessageBox.DestructiveRole)
        cancel_button = msg_box.addButton(self.translator.tr("cancel"), QMessageBox.RejectRole)
        
        msg_box.exec()
        
        if msg_box.clickedButton() == hide_button:
            self.hide()
            self.tray.show()
            e.ignore()
        elif msg_box.clickedButton() == exit_button:
            clear_and_exit()
            e.accept()
        else: # Cancel
            e.ignore()

    def create_actions(self):
        """Creates all QAction objects for menus and shortcuts."""
        self.save_action = QAction(self)
        self.save_action.setShortcut(self.config["shortcuts"].get("save", "Ctrl+S"))
        self.save_action.triggered.connect(self.save_config_and_restart_daemon)
        self.addAction(self.save_action)

        self.quit_action = QAction(self)
        self.quit_action.setShortcut(self.config["shortcuts"].get("quit", "Ctrl+Q"))
        self.quit_action.triggered.connect(clear_and_exit)
        self.addAction(self.quit_action)

        # Akcje dla zakładki Stacje
        self.add_station_action = QAction(self)
        self.add_station_action.setShortcut(self.config["shortcuts"].get("add_station", "Ctrl+N"))
        self.add_station_action.triggered.connect(self.add_station)
        self.addAction(self.add_station_action)

        self.edit_station_action = QAction(self)
        self.edit_station_action.setShortcut(self.config["shortcuts"].get("edit_station", "Ctrl+E"))
        self.edit_station_action.triggered.connect(self.edit_station)
        self.addAction(self.edit_station_action)

        self.delete_station_action = QAction(self)
        self.delete_station_action.setShortcut(self.config["shortcuts"].get("delete_station", "Del"))
        self.delete_station_action.triggered.connect(self.delete_station)
        self.addAction(self.delete_station_action)

        self.play_station_action = QAction(self)
        self.play_station_action.setShortcut(self.config["shortcuts"].get("play_station", "F5"))
        self.play_station_action.triggered.connect(self.play_from_tree)
        self.addAction(self.play_station_action)

        # Skróty do zmiany kolejności (bez akcji, bo są specyficzne dla kontekstu)
        QShortcut(QKeySequence(self.config["shortcuts"].get("move_up", "Ctrl+Up")), self, self.move_station_up)
        QShortcut(QKeySequence(self.config["shortcuts"].get("move_down", "Ctrl+Down")), self, self.move_station_down)

        # Akcje dla ulubionych
        self.add_to_favorites_action = QAction(self)
        self.add_to_favorites_action.triggered.connect(lambda: self.toggle_favorite_status(True))
        self.addAction(self.add_to_favorites_action)

        self.remove_from_favorites_action = QAction(self)
        self.remove_from_favorites_action.triggered.connect(lambda: self.toggle_favorite_status(False))
        self.addAction(self.remove_from_favorites_action)

        self.set_as_default_action = QAction(self)
        self.set_as_default_action.triggered.connect(self.set_as_default_station)
        self.addAction(self.set_as_default_action)

        self.restart_daemon_action = QAction(self)
        self.restart_daemon_action.triggered.connect(self.restart_scheduler_daemon)
        self.addAction(self.restart_daemon_action)


    def create_tray_icon(self):
        """Creates and configures the system tray icon and its menu."""
        self.tray = QSystemTrayIcon(self.style().standardIcon(DEFAULT_ICON), self)
        self.tray.setToolTip("RadioScheduler")
        self.build_tray_menu()
        self.tray.show()
        self.tray.installEventFilter(self)
        self.tray.activated.connect(self.on_tray_activated)

    def on_tray_activated(self, reason):
        """Handles clicks on the tray icon."""
        if reason == QSystemTrayIcon.Trigger: # Lewy klik
            self.show()
        elif reason == QSystemTrayIcon.Context: # Prawy klik
            self.build_tray_menu() # Odśwież menu przed pokazaniem


    def eventFilter(self, obj, event):
        """Filters events, used here to catch mouse wheel events on the tray icon for volume control."""
        if obj is self.tray and event.type() == QEvent.Wheel:
            delta = event.angleDelta().y()
            current_volume = mpc.get_volume()
            if delta > 0:
                mpc.set_volume(current_volume + 2)
            else:
                mpc.set_volume(current_volume - 2)
            self.update_tray_tooltip()
        return super().eventFilter(obj, event)

    def update_tray_icon(self):
        """Updates the tray icon to reflect the current mode (manual override or schedule)."""
        icon_enum = MANUAL_ICON if MANUAL_OVERRIDE_LOCK.exists() else DEFAULT_ICON
        icon = self.style().standardIcon(icon_enum)
        self.tray.setIcon(icon)

    def build_tray_menu(self):
        """Builds or rebuilds the context menu for the system tray icon."""
        menu = QMenu()
        favorites = [s for s in self.config.get("stations", []) if s.get("favorite")]

        menu.addAction(self.translator.tr("now_playing", current=mpc.get_current())).setEnabled(False)
        menu.addSeparator() # Separator for favorites

        if favorites:
            for s in favorites:
                a = menu.addAction(f"★ {s['name']}")
                a.triggered.connect(lambda _, x=s: (play_now(x), self.update_return_to_schedule_button()))
        else:
            menu.addAction(self.translator.tr("no_favorites")).setEnabled(False)

        menu.addSeparator() # Separator for volume

        vol_menu = menu.addMenu(self.translator.tr("volume_menu", volume=mpc.get_volume()))
        for v in range(0, 101, 5):
            a = vol_menu.addAction(f"{v:3}%")
            a.triggered.connect(lambda _, vol=v: (mpc.set_volume(vol), self.build_tray_menu()))

        menu.addSeparator()
        
        if MANUAL_OVERRIDE_LOCK.exists():
            return_action = menu.addAction(self.translator.tr("return_to_schedule"))
            return_action.triggered.connect(self.return_to_schedule)
            menu.addSeparator()
        
        menu.addAction(self.restart_daemon_action)
        menu.addSeparator() # Separator before show/quit
        menu.addAction(self.translator.tr("show_editor"), self.show)
        menu.addAction(self.translator.tr("exit"), clear_and_exit)
        self.tray.setContextMenu(menu)
        self.update_tray_tooltip()

    def update_tray_tooltip(self):
        """Updates the tooltip for the tray icon with current status."""
        current = mpc.get_current()
        vol = mpc.get_volume()
        self.tray.setToolTip(f"RadioScheduler\n{self.translator.tr('now_playing', current=current)}\n{self.translator.tr('volume_menu', volume=vol)}")

    def on_timer_tick(self):
        """Periodic timer handler to refresh dynamic UI elements."""
        current_song_url = mpc.get_current_url() # type: ignore
        # Odświeżaj tylko, jeśli coś się zmieniło
        if current_song_url != self.last_known_song:
            self.last_known_song = current_song_url
            self.update_tray_tooltip()
            self.update_playing_station_in_tree() # Użyj nowej, wydajnej metody
            self.update_tray_icon()

        # Odświeżaj zakładkę "About" i metadane utworu tylko, gdy okno jest widoczne
        if self.isVisible():
            self.about_tab.update_content()
            self.now_playing_label.setText(mpc.get_current()) # type: ignore # Aktualizuj etykietę

    def show(self):
        super().show()
        self.activateWindow()

    def load_config(self):
        """Loads the configuration from the YAML file, merging it with defaults to ensure all keys exist."""
        # Default shortcuts
        default_shortcuts = {
            "save": "Ctrl+S", "quit": "Ctrl+Q", "add_station": "Ctrl+N",
            "edit_station": "Ctrl+E", "delete_station": "Del", "play_station": "F5",
            "move_up": "Ctrl+Up", "move_down": "Ctrl+Down"
        }
        default = {
            "stations": [],
            "schedule": {
                "default": "",
                "weekly": [],
                "news_breaks": {
                    "enabled": True,
                    "start_minute_offset": 55,
                    "use_advanced": False,
                    "simple": {"station": "TOK FM – News", "days": ["mon","tue","wed","thu","fri"],
                               "from": "06:00", "to": "20:00", "interval_minutes": 30, "duration_minutes": 8},
                    "advanced": []
                },
            },
            "language": "pl", # Default language
            "shortcuts": default_shortcuts # Default shortcuts

        }
        if not CONFIG_PATH.exists():
            return default
        try:
            # Load existing config
            with open(CONFIG_PATH, "r", encoding="utf-8") as f:
                user_config = yaml.safe_load(f) or {}

            # Deep merge user config into defaults
            default.update(user_config)
            if 'schedule' in user_config:
                default['schedule'].update(user_config['schedule'])
            if 'shortcuts' in user_config:
                default['shortcuts'].update(user_config['shortcuts'])

        except Exception as e:
            logging.critical(f"Błąd odczytu pliku konfiguracyjnego: {e}", exc_info=True)
            QMessageBox.critical(self, self.translator.tr("critical_error"), self.translator.tr("config_load_error", e=e))
        return default

    def retranslate_ui(self):
        """Updates all UI text elements to the currently selected language."""
        self.setWindowTitle(self.translator.tr("app_title"))
        
        # Retranslate actions
        self.save_action.setText(self.translator.tr("save"))
        self.quit_action.setText(self.translator.tr("exit"))
        self.add_station_action.setText(self.translator.tr("add_station"))
        self.edit_station_action.setText(self.translator.tr("edit_station"))
        self.delete_station_action.setText(self.translator.tr("delete_station"))
        self.play_station_action.setText(self.translator.tr("play_station"))
        self.add_to_favorites_action.setText(self.translator.tr("add_to_favorites"))
        self.remove_from_favorites_action.setText(self.translator.tr("remove_from_favorites"))
        self.set_as_default_action.setText(self.translator.tr("set_as_default"))
        self.restart_daemon_action.setText(self.translator.tr("restart_daemon"))

        self.tabs.setTabText(0, self.translator.tr("stations_tab_title"))
        self.tabs.setTabText(1, self.translator.tr("schedule_tab_title"))
        self.tabs.setTabText(2, self.translator.tr("news_tab_title"))
        self.tabs.setTabText(3, self.translator.tr("settings_tab_title"))
        self.tabs.setTabText(4, self.translator.tr("mpd_config_tab_title"))
        self.tabs.setTabText(5, self.translator.tr("about_tab_title"))
        # Explicitly call retranslate on the child widget
        self.about_tab.update_content()

    def restart_scheduler_daemon(self):
        """Restarts the background scheduler daemon process."""
        subprocess.run(["pkill", "-f", "radio-scheduler.py"], check=False)
        subprocess.Popen([sys.executable, str(DAEMON_PATH)], start_new_session=True)
        QMessageBox.information(self, self.translator.tr("restart_daemon"), self.translator.tr("daemon_restarted"))

    # === STACJE ===
    def tab_stations(self):
        """Creates the 'Stations' tab widget."""
        w = QWidget()
        l = QHBoxLayout(w)
        self.tree = QTreeWidget()
        self.tree.setHeaderLabels([self.translator.tr("stations_tab_title")])
        self.tree.header().setVisible(False)
        self.tree.itemDoubleClicked.connect(self.play_from_tree)
        # Ustawienie polityki menu kontekstowego
        self.tree.setContextMenuPolicy(Qt.CustomContextMenu)
        self.tree.customContextMenuRequested.connect(self.show_station_context_menu)
        self.refresh_tree()
        l.addWidget(self.tree, 3)

        btns = QVBoxLayout()
        add = QPushButton(self.translator.tr("add")); add.clicked.connect(self.add_station_action.trigger)
        add.setStyleSheet("background-color: #4CAF50; color: white;")
        edit = QPushButton(self.translator.tr("edit")); edit.clicked.connect(self.edit_station_action.trigger)
        edit.setStyleSheet("background-color: #2196F3; color: white;")
        delete = QPushButton(self.translator.tr("delete")); delete.clicked.connect(self.delete_station_action.trigger)
        delete.setStyleSheet("background-color: #f44336; color: white;")

        play = QPushButton(self.translator.tr("play_now")); play.clicked.connect(self.play_station_action.trigger)
        self.return_to_schedule_btn = QPushButton(self.translator.tr("return_to_schedule"))

        # Przyciski do zmiany kolejności
        reorder_layout = QHBoxLayout()
        move_up_btn = QPushButton(self.translator.tr("move_up")); move_up_btn.clicked.connect(self.move_station_up)
        move_down_btn = QPushButton(self.translator.tr("move_down")); move_down_btn.clicked.connect(self.move_station_down)
        reorder_layout.addWidget(move_up_btn)
        reorder_layout.addWidget(move_down_btn)
        
        self.return_to_schedule_btn.clicked.connect(self.return_to_schedule) # Connect to the correct method
        self.update_return_to_schedule_button()

        play.setStyleSheet("background-color: #4CAF50; color: white; font-weight: bold;")
        self.return_to_schedule_btn.setStyleSheet("background-color: #f44336; color: white;")

        volume_slider = QSlider(Qt.Horizontal)
        volume_slider.setRange(0, 100)
        volume_slider.setValue(mpc.get_volume()) # Initial volume
        volume_slider.valueChanged.connect(mpc.set_volume)
        volume_label = QLabel(self.translator.tr("volume"))
        self.tree.setFocus() # Ustaw fokus na drzewie, aby skróty od razu działały

        # Przycisk Zastosuj dla stacji
        self.apply_stations_btn = QPushButton(self.translator.tr("apply_stations"))
        self.apply_stations_btn.clicked.connect(self.save_stations_only)
        self.apply_stations_btn.setEnabled(False) # Domyślnie wyłączony
        self.apply_stations_btn.setStyleSheet("background-color: #008CBA; color: white;")

        btns.addWidget(add); btns.addWidget(edit); btns.addWidget(delete)
        btns.addSpacing(20)
        btns.addLayout(reorder_layout)
        btns.addSpacing(20)
        btns.addWidget(play)
        btns.addWidget(self.return_to_schedule_btn)
        btns.addStretch()
        btns.addWidget(self.apply_stations_btn)
        btns.addSpacing(10)
        btns.addWidget(volume_label)
        btns.addWidget(volume_slider)

        # Etykieta na aktualnie grany utwór
        self.now_playing_label = QLabel(self.translator.tr("now_playing", current=mpc.get_current()))
        self.now_playing_label.setWordWrap(True)
        btns.addWidget(self.now_playing_label)
        l.addLayout(btns, 1)
        return w

    def update_playing_station_in_tree(self):
        """Efficiently updates the currently playing station in the tree without a full rebuild."""
        current_url = self.last_known_song # Użyj zbuforowanej wartości
        iterator = QTreeWidgetItemIterator(self.tree)
        while iterator.value():
            item = iterator.value()
            # Działaj tylko na elementach-dzieciach (stacjach)
            if item.parent():
                station_data = item.data(0, Qt.UserRole)
                is_playing = station_data and station_data.get('url') == current_url

                font = item.font(0)
                font.setBold(is_playing)
                item.setFont(0, font)

                icon = self.style().standardIcon(QStyle.SP_MediaPlay) if is_playing else QIcon()
                item.setIcon(0, icon)

            iterator += 1

    def refresh_tree(self, mark_dirty=False):
        """Refreshes the station tree view, optionally marking the state as dirty (needs saving)."""
        self.tree.clear()
        current_url = mpc.get_current_url()
        groups = defaultdict(list)
        for s in self.stations: # Use self.stations directly
            g = s.get("genre") or self.translator.tr("genre_none")
            groups[g].append(s)
        for genre, stations in sorted(groups.items()):
            parent = QTreeWidgetItem(self.tree, [genre])
            parent.setFlags(parent.flags() & ~Qt.ItemIsSelectable)
            for s in stations:
                name = f"★ {s['name']}" if s.get("favorite") else s["name"]
                item = QTreeWidgetItem(parent, [name])
                item.setData(0, Qt.UserRole, s)
                if s['url'] == current_url:
                    font = item.font(0)
                    font.setBold(True)
                    item.setFont(0, font)
                    item.setIcon(0, self.style().standardIcon(QStyle.SP_MediaPlay))
        self.tree.expandAll()
        if mark_dirty:
            self.apply_stations_btn.setEnabled(True)

    def show_station_context_menu(self, position):
        """Shows the context menu for a station item in the tree."""
        item = self.tree.itemAt(position)
        # Pokaż menu tylko dla elementów stacji (które mają rodzica)
        if not item or item.parent() is None:
            return

        menu = QMenu()
        
        # Akcje podstawowe
        menu.addAction(self.play_station_action)
        menu.addAction(self.edit_station_action)
        menu.addAction(self.delete_station_action)

        # Akcje ulubionych
        station_data = item.data(0, Qt.UserRole)
        if station_data:
            menu.addSeparator()
            if station_data.get("favorite"):
                menu.addAction(self.remove_from_favorites_action) # Use the action
            else:
                menu.addAction(self.add_to_favorites_action) # Use the action

        menu.addSeparator()
        menu.addAction(self.set_as_default_action) # Use the action

        menu.exec(self.tree.viewport().mapToGlobal(position))

    def toggle_favorite_status(self, is_favorite):
        """Toggles the favorite status of the currently selected station."""
        item = self.tree.currentItem()
        if not item or item.parent() is None: return
        station = item.data(0, Qt.UserRole)
        if not station: return

        # Znajdź stację na głównej liście i zaktualizuj ją
        for i, s in enumerate(self.stations):
            if s["url"] == station["url"]:
                self.stations[i]["favorite"] = is_favorite
                self.refresh_tree(mark_dirty=True) # Oznacz zmiany jako brudne
                return

    def set_as_default_station(self):
        """Sets the currently selected station as the default fallback station."""
        item = self.tree.currentItem()
        if not item or item.parent() is None: return
        station = item.data(0, Qt.UserRole)
        if not station: return

        station_name = station.get("name")
        self.schedule["default"] = station_name
        # Zmiana domyślnej stacji powinna być zapisana z harmonogramem
        # Zamiast natychmiastowego zapisu, można by tu ustawić flagę
        self.save_schedule() # Na razie zostawiamy zapis, ale idealnie byłoby to zmienić

    def play_from_tree(self):
        """Plays the currently selected station from the tree."""
        item = self.tree.currentItem()
        if not item or item.parent() is None: return
        station = item.data(0, Qt.UserRole)
        if station:
            play_now(station)
            # Natychmiast zaktualizuj bufor, aby interfejs odświeżył się od razu
            self.last_known_song = station.get("url")
            self.update_return_to_schedule_button()
            self.update_playing_station_in_tree() # Użyj wydajnej metody
            self.update_tray_icon()

    def return_to_schedule(self):
        """Removes the manual override lock, allowing the scheduler to take control again."""
        MANUAL_OVERRIDE_LOCK.unlink(missing_ok=True)
        self.update_return_to_schedule_button()
        self.build_tray_menu() # Odśwież menu w trayu
        self.update_tray_icon()

    def update_return_to_schedule_button(self):
        """Shows or hides the 'Return to Schedule' button based on the manual override lock."""
        self.return_to_schedule_btn.setVisible(MANUAL_OVERRIDE_LOCK.exists())

    def add_station(self): self.edit_station()

    def move_station_up(self):
        self.move_station(-1)

    def move_station_down(self):
        self.move_station(1)

    def move_station(self, direction):
        """Moves the selected station up or down in the list."""
        item = self.tree.currentItem()
        if not item or item.parent() is None: return
        station = item.data(0, Qt.UserRole)
        if not station: return

        idx = self.stations.index(station)
        new_idx = idx + direction
        if 0 <= new_idx < len(self.stations):
            self.stations.pop(idx)
            self.stations.insert(new_idx, station)
            self.refresh_tree(mark_dirty=True)

    def edit_station(self):
        """Opens a dialog to add a new station or edit the currently selected one."""
        item = self.tree.currentItem()
        station = item.data(0, Qt.UserRole) if item and item.parent() else {}
        dlg = QDialog(self) # Create a dialog
        dlg.setWindowTitle(self.translator.tr("add_station") if not station else self.translator.tr("edit_station"))
        l = QFormLayout(dlg)
        name = QLineEdit(station.get("name", ""))
        url = QLineEdit(station.get("url", ""))
        genre = QLineEdit(station.get("genre", ""))
        fav = QCheckBox(self.translator.tr("favorite")); fav.setChecked(station.get("favorite", False))
        l.addRow(self.translator.tr("name"), name); l.addRow(self.translator.tr("url"), url); l.addRow(self.translator.tr("genre"), genre); l.addRow("", fav)
        btns = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        btns.accepted.connect(dlg.accept); btns.rejected.connect(dlg.reject)
        l.addRow(btns)
        if dlg.exec() == QDialog.Accepted:
            new = {"name": name.text().strip(), "url": url.text().strip(),
                   "genre": genre.text().strip() or None, "favorite": fav.isChecked()}
            if not new["name"] or not new["url"]: # Check for empty name/url
                QMessageBox.warning(self, self.translator.tr("error"), self.translator.tr("name_and_url_required"))
                return
            if station:
                idx = self.stations.index(station)
                self.stations[idx] = new
            else:
                self.stations.append(new)
            self.config["stations"] = self.stations # Update config
            self.refresh_tree(mark_dirty=True)
            # Nie zapisujemy od razu, użytkownik kliknie "Zastosuj"

    def delete_station(self): # Delete station
        """Deletes the currently selected station after confirmation."""
        item = self.tree.currentItem()
        if not item or item.parent() is None: return
        s = item.data(0, Qt.UserRole)
        if QMessageBox.question(self, self.translator.tr("delete_prompt"), self.translator.tr("delete_station_prompt", name=s['name'])) == QMessageBox.Yes:
            self.stations.remove(s)
            self.config["stations"] = self.stations
            self.refresh_tree(mark_dirty=True)
            # Nie zapisujemy od razu, użytkownik kliknie "Zastosuj"
    # === HARMONOGRAM + NEWS + ABOUT ===
    def tab_schedule(self):
        """Creates the 'Schedule' tab widget."""
        w = QWidget()
        l = QHBoxLayout(w)

        # Lewa strona - lista reguł
        left_vbox = QVBoxLayout() # Left side for schedule rules
        left_vbox.addWidget(QLabel(self.translator.tr("schedule_rules")))
        self.schedule_list = QListWidget()
        self.schedule_list.setSelectionMode(QAbstractItemView.SingleSelection)
        self.refresh_schedule_list()
        left_vbox.addWidget(self.schedule_list)

        # Domyślna stacja
        default_station_form = QFormLayout()
        self.default_station_combo = QComboBox()
        self.refresh_default_station_combo()
        default_station_form.addRow(self.translator.tr("default_station_label"), self.default_station_combo)
        left_vbox.addLayout(default_station_form)
        l.addLayout(left_vbox, 2)

        # Prawa strona - przyciski
        btns = QVBoxLayout() # Buttons for schedule rules
        add = QPushButton(self.translator.tr("add_rule")); add.clicked.connect(self.add_schedule_rule); 
        add.setStyleSheet("background-color: #4CAF50; color: white;")
        edit = QPushButton(self.translator.tr("edit_rule")); edit.clicked.connect(self.edit_schedule_rule)
        edit.setStyleSheet("background-color: #2196F3; color: white;")
        delete = QPushButton(self.translator.tr("delete_rule")); delete.clicked.connect(self.delete_schedule_rule)
        delete.setStyleSheet("background-color: #f44336; color: white;")
        save = QPushButton(self.translator.tr("save_changes")); save.clicked.connect(self.save_schedule)
        save.setStyleSheet("background-color: #4CAF50; color: white; font-weight: bold;")
        btns.addWidget(add); btns.addWidget(edit); btns.addWidget(delete)
        btns.addStretch(); btns.addWidget(save); btns.addStretch()
        l.addLayout(btns, 1)
        return w

    def refresh_default_station_combo(self):
        """Refreshes the contents of the default station dropdown."""
        self.default_station_combo.clear()
        self.default_station_combo.addItem(self.translator.tr("no_station"), None)
        for s in self.stations:
            self.default_station_combo.addItem(s["name"], s["name"])
        idx = self.default_station_combo.findData(self.schedule.get("default"))
        if idx > -1: self.default_station_combo.setCurrentIndex(idx)

    def refresh_schedule_list(self):
        """Refreshes the list of schedule rules."""
        self.schedule_list.clear()
        day_map = {
            "mon": self.translator.tr("day_mon_short"), "tue": self.translator.tr("day_tue_short"),
            "wed": self.translator.tr("day_wed_short"), "thu": self.translator.tr("day_thu_short"),
            "fri": self.translator.tr("day_fri_short"), "sat": self.translator.tr("day_sat_short"), "sun": self.translator.tr("day_sun_short")
        }
        for i, rule in enumerate(self.schedule.get("weekly", [])):
            days = ", ".join([day_map.get(d, d) for d in rule["days"]])
            item = QListWidgetItem(f"{days}: {rule['from']}–{rule['to']} → {rule['station']}")
            item.setData(Qt.UserRole, i)
            self.schedule_list.addItem(item)

    def add_schedule_rule(self):
        """Opens a dialog to add a new schedule rule."""
        dlg = TimeRangeEditor(tree=self.tree, parent=self)
        rule = dlg.get_rule()
        if rule:
            self.schedule.setdefault("weekly", []).append(rule)
            # Zmiana na zapis po kliknięciu przycisku
            self.refresh_schedule_list()

    def edit_schedule_rule(self):
        """Opens a dialog to edit the selected schedule rule."""
        item = self.schedule_list.currentItem()
        if not item: return
        idx = item.data(Qt.UserRole)
        rule = self.schedule["weekly"][idx]
        dlg = TimeRangeEditor(rule, self.tree, self)
        new_rule = dlg.get_rule()
        if new_rule:
            self.schedule["weekly"][idx] = new_rule
            # Zmiana na zapis po kliknięciu przycisku
            self.refresh_schedule_list()

    def delete_schedule_rule(self):
        """Deletes the selected schedule rule after confirmation."""
        item = self.schedule_list.currentItem()
        if not item: return
        if QMessageBox.question(self, self.translator.tr("delete_prompt"), self.translator.tr("delete_rule_prompt")) == QMessageBox.Yes:
            idx = item.data(Qt.UserRole)
            del self.schedule["weekly"][idx]
            # Zmiana na zapis po kliknięciu przycisku
            self.refresh_schedule_list()

    def save_stations_only(self):
        """Saves only the station list to the config file without restarting the daemon."""
        self.config["stations"] = self.stations
        try:
            CONFIG_PATH.parent.mkdir(parents=True, exist_ok=True)
            with open(CONFIG_PATH, "w", encoding="utf-8") as f:
                yaml.safe_dump(self.config, f, allow_unicode=True, sort_keys=False)
            self.apply_stations_btn.setEnabled(False) # Disable button after saving
            # Optionally, show a temporary status message
            self.statusBar().showMessage(self.translator.tr("stations_saved_success"), 3000)
        except Exception as e:
            logging.error(f"Błąd zapisu pliku konfiguracyjnego (tylko stacje): {e}")
            QMessageBox.critical(self, self.translator.tr("save_error"), self.translator.tr("config_save_error", e=e))

    def save_config_and_restart_daemon(self):
        """Collects data from all tabs, saves the config file, and restarts the daemon."""
        # Zbierz dane z zakładek Harmonogram i Wiadomości
        self.schedule["default"] = self.default_station_combo.currentData()
        self.save_news_config()
        self.config["schedule"] = self.schedule
        # self.config["stations"] jest już aktualne
        try:
            CONFIG_PATH.parent.mkdir(parents=True, exist_ok=True)
            with open(CONFIG_PATH, "w", encoding="utf-8") as f:
                yaml.safe_dump(self.config, f, allow_unicode=True, sort_keys=False)
            QMessageBox.information(self, self.translator.tr("ok"), self.translator.tr("saved_daemon_restarted"))
            subprocess.run(["pkill", "-f", "radio-scheduler.py"], check=False) # Kill existing daemon
            subprocess.Popen([sys.executable, str(DAEMON_PATH)], start_new_session=True)
        except Exception as e:
            logging.error(f"Błąd zapisu pliku konfiguracyjnego: {e}")
            QMessageBox.critical(self, self.translator.tr("save_error"), self.translator.tr("config_save_error", e=e))

    def save_schedule(self):
        self.save_config_and_restart_daemon()

    def tab_news(self):
        """Creates the 'News Service' tab widget."""
        self.news_tab_widget = QWidget()
        self.news_config = self.schedule.get("news_breaks", {})
        
        main_layout = QVBoxLayout(self.news_tab_widget)
        
        # --- General settings ---
        self.news_enabled = QCheckBox(self.translator.tr("enable_news"))
        self.news_enabled.setChecked(self.news_config.get("enabled", True))
        
        offset_layout = QHBoxLayout()
        offset_layout.addWidget(QLabel(self.translator.tr("news_offset_label")))
        self.news_offset = QSpinBox(minimum=0, maximum=59, value=self.news_config.get("start_minute_offset", 0))
        offset_layout.addWidget(self.news_offset)
        offset_layout.addStretch()

        main_layout.addWidget(self.news_enabled)
        main_layout.addLayout(offset_layout)
        main_layout.addSpacing(10)

        # --- Mode selection ---
        mode_group = QGroupBox(self.translator.tr("config_mode"))
        mode_layout = QHBoxLayout(mode_group)
        self.simple_mode_radio = QRadioButton(self.translator.tr("simple_mode"))
        self.advanced_mode_radio = QRadioButton(self.translator.tr("advanced_mode"))
        mode_layout.addWidget(self.simple_mode_radio)
        mode_layout.addWidget(self.advanced_mode_radio)
        main_layout.addWidget(mode_group)

        # --- Simple Mode UI ---
        self.simple_box = QGroupBox(self.translator.tr("simple_mode_title"))
        simple_layout = QFormLayout(self.simple_box)
        simple_cfg = self.news_config.get("simple", {})
        self.news_station = QComboBox()
        self.news_station.addItems([s['name'] for s in self.stations if "News" in s['name'] or "Wiadomości" in s['name']] + [s['name'] for s in self.stations])
        idx = self.news_station.findText(simple_cfg.get("station", ""))
        if idx > -1: self.news_station.setCurrentIndex(idx)
        self.news_from = QTimeEdit(time.fromisoformat(simple_cfg.get("from", "06:00")))
        self.news_to = QTimeEdit(time.fromisoformat(simple_cfg.get("to", "20:00")))
        self.news_interval = QSpinBox(minimum=15, maximum=120, value=simple_cfg.get("interval_minutes", 30), singleStep=15)
        self.news_duration = QSpinBox(minimum=1, maximum=15, value=simple_cfg.get("duration_minutes", 8))
        simple_layout.addRow(self.translator.tr("station"), self.news_station); simple_layout.addRow(self.translator.tr("from"), self.news_from); simple_layout.addRow(self.translator.tr("to"), self.news_to); simple_layout.addRow(self.translator.tr("interval_minutes"), self.news_interval); simple_layout.addRow(self.translator.tr("duration_minutes"), self.news_duration)
        main_layout.addWidget(self.simple_box)

        # --- Advanced Mode UI ---
        self.advanced_box = QWidget()
        adv_layout = QHBoxLayout(self.advanced_box)
        self.news_rules_list = QListWidget()
        self.refresh_news_rules_list() # Refresh list
        adv_layout.addWidget(self.news_rules_list, 2)
        
        adv_btns = QVBoxLayout()
        add = QPushButton(self.translator.tr("add_rule")); add.clicked.connect(self.add_news_rule); 
        add.setStyleSheet("background-color: #4CAF50; color: white;")
        edit = QPushButton(self.translator.tr("edit_rule")); edit.clicked.connect(self.edit_news_rule)
        edit.setStyleSheet("background-color: #2196F3; color: white;")
        delete = QPushButton(self.translator.tr("delete_rule")); delete.clicked.connect(self.delete_news_rule)
        delete.setStyleSheet("background-color: #f44336; color: white;")
        adv_btns.addWidget(add); adv_btns.addWidget(edit); adv_btns.addWidget(delete); adv_btns.addStretch()
        adv_layout.addLayout(adv_btns, 1)
        main_layout.addWidget(self.advanced_box)

        # --- Save Button ---
        save_btn = QPushButton(self.translator.tr("save_changes"))
        save_btn.clicked.connect(self.save_schedule) # Reuse the same save logic
        save_btn.setStyleSheet("background-color: #4CAF50; color: white; font-weight: bold;")
        main_layout.addWidget(save_btn, 0, Qt.AlignRight)

        # --- Logic to switch modes ---
        self.simple_mode_radio.toggled.connect(self.toggle_news_mode)
        if self.news_config.get("use_advanced", False):
            self.advanced_mode_radio.setChecked(True)
        else:
            self.simple_mode_radio.setChecked(True)

        main_layout.addStretch()
        return self.news_tab_widget

    def toggle_news_mode(self, checked):
        """Switches the news configuration UI between simple and advanced modes."""
        if checked: # Simple mode is on
            self.simple_box.show()
            self.advanced_box.hide()
        else: # Advanced mode is on
            self.simple_box.hide()
            self.advanced_box.show()

    def refresh_news_rules_list(self):
        """Refreshes the list of advanced news rules."""
        self.news_rules_list.clear()
        day_map = {"mon": "Pn", "tue": "Wt", "wed": "Śr", "thu": "Cz", "fri": "Pt", "sat": "So", "sun": "Nd"}
        for i, rule in enumerate(self.news_config.get("advanced", [])):
            days = ", ".join([day_map.get(d, d) for d in rule["days"]])
            item = QListWidgetItem(f"{days}: {rule['from']}–{rule['to']} → {rule['station']} (co {rule['interval_minutes']} min)")
            item.setData(Qt.UserRole, i)
            self.news_rules_list.addItem(item)

    def add_news_rule(self):
        """Opens a dialog to add a new advanced news rule."""
        dlg = TimeRangeEditor(tree=self.tree, parent=self, is_news_rule=True)
        rule = dlg.get_rule()
        if rule:
            self.news_config.setdefault("advanced", []).append(rule)
            self.refresh_news_rules_list()

    def edit_news_rule(self):
        """Opens a dialog to edit the selected advanced news rule."""
        item = self.news_rules_list.currentItem()
        if not item: return
        idx = item.data(Qt.UserRole)
        rule = self.news_config["advanced"][idx]
        dlg = TimeRangeEditor(rule, self.tree, self, is_news_rule=True)
        new_rule = dlg.get_rule()
        if new_rule:
            self.news_config["advanced"][idx] = new_rule
            self.refresh_news_rules_list()

    def delete_news_rule(self):
        """Deletes the selected advanced news rule after confirmation."""
        item = self.news_rules_list.currentItem()
        if not item: return
        if QMessageBox.question(self, self.translator.tr("delete_prompt"), self.translator.tr("delete_news_rule_prompt")) == QMessageBox.Yes:
            idx = item.data(Qt.UserRole)
            del self.news_config["advanced"][idx]
            self.refresh_news_rules_list()

    def save_news_config(self):
        """Collects news configuration data from the UI widgets."""
        self.news_config["enabled"] = self.news_enabled.isChecked()
        self.news_config["use_advanced"] = self.advanced_mode_radio.isChecked()
        self.news_config["start_minute_offset"] = self.news_offset.value()
        self.news_config["simple"] = {
            "station": self.news_station.currentText(),
            "from": self.news_from.time().toString("HH:mm"),
            "to": self.news_to.time().toString("HH:mm"),
            "interval_minutes": self.news_interval.value(),
            "duration_minutes": self.news_duration.value()
        }
        # Zaawansowane reguły są już w self.news_config["advanced"]

    # === MPD CONFIG EDITOR ===
    def tab_mpd_config(self):
        """Creates the 'MPD Config' tab widget with a text editor."""
        w = QWidget()
        self.mpd_config_layout = QVBoxLayout(w)

        self.mpd_conf_path = Path.home() / ".config/mpd/mpd.conf"

        info_label = QLabel(self.translator.tr("editing_file", path=self.mpd_conf_path))
        info_label.setTextFormat(Qt.RichText)
        self.mpd_config_layout.addWidget(info_label)

        self.mpd_conf_editor = QTextEdit()
        self.mpd_conf_editor.setFont(QFont("Monospace", 10))
        self.mpd_config_layout.addWidget(self.mpd_conf_editor)

        self.load_mpd_config()

        button_layout = QHBoxLayout()
        reload_btn = QPushButton(self.translator.tr("reload"))
        reload_btn.clicked.connect(self.load_mpd_config)
        reload_btn.setStyleSheet("background-color: #2196F3; color: white;")
        save_btn = QPushButton(self.translator.tr("save_changes"))
        save_btn.clicked.connect(self.save_mpd_config)
        save_btn.setStyleSheet("background-color: #4CAF50; color: white; font-weight: bold;")
        restart_btn = QPushButton(self.translator.tr("restart_mpd"))
        restart_btn.clicked.connect(self.restart_mpd)
        restart_btn.setStyleSheet("background-color: #ff9800; color: white; font-weight: bold;")

        button_layout.addStretch()
        button_layout.addWidget(reload_btn)
        button_layout.addWidget(restart_btn)
        button_layout.addWidget(save_btn)
        self.mpd_config_layout.addLayout(button_layout)

        return w

    def load_mpd_config(self):
        """Loads the content of the mpd.conf file into the text editor."""
        try:
            if self.mpd_conf_path.exists():
                content = self.mpd_conf_path.read_text(encoding="utf-8")
                self.mpd_conf_editor.setPlainText(content)
            else:
                self.mpd_conf_editor.setPlainText(f"# Plik nie istnieje: {self.mpd_conf_path}\n"
                                                  "# Możesz utworzyć podstawową konfigurację i zapisać plik.")
        except Exception as e:
            QMessageBox.critical(self, self.translator.tr("read_error"), self.translator.tr("mpd_conf_read_error", e=e))
            logging.error(f"Błąd odczytu pliku mpd.conf: {e}")

    def save_mpd_config(self):
        """Saves the content of the text editor to the mpd.conf file."""
        try:
            content = self.mpd_conf_editor.toPlainText()
            self.mpd_conf_path.parent.mkdir(parents=True, exist_ok=True)
            self.mpd_conf_path.write_text(content, encoding="utf-8")
            QMessageBox.information(self, self.translator.tr("saved"), self.translator.tr("mpd_conf_save_success", path=self.mpd_conf_path))
        except Exception as e:
            QMessageBox.critical(self, self.translator.tr("save_error"), self.translator.tr("mpd_conf_save_error", e=e))
            logging.error(f"Błąd zapisu pliku mpd.conf: {e}")

    def restart_mpd(self):
        """Restarts the MPD service."""
        try:
            # Najpierw spróbuj zabić działającą instancję MPD
            kill_result = subprocess.run(["mpd", "--kill"], capture_output=True, text=True, check=False)
            # This string is from the 'mpd' command itself, so it's likely in English.
            # We don't translate it.
            if kill_result.returncode != 0 and "No running MPD instance" not in kill_result.stderr:
                 QMessageBox.warning(self, self.translator.tr("error"), self.translator.tr("mpd_stop_error", stderr=kill_result.stderr))
                 return

            # Poczekaj chwilę na zamknięcie
            time.sleep(0.5)

            # Uruchom MPD ponownie
            start_result = subprocess.run(["mpd"], capture_output=True, text=True, check=False)
            if start_result.returncode != 0: # Check for errors
                QMessageBox.critical(self, self.translator.tr("error"), self.translator.tr("mpd_restart_error", stderr=start_result.stderr))
            else:
                QMessageBox.information(self, self.translator.tr("success"), self.translator.tr("mpd_restarted"))
        except Exception as e:
            QMessageBox.critical(self, self.translator.tr("critical_error"), self.translator.tr("mpd_critical_error", e=e))
            logging.error(f"Błąd krytyczny podczas restartu MPD: {e}")

    # === SETTINGS TAB ===
    def tab_settings(self):
        """Creates the 'Settings' tab widget."""
        w = QWidget()
        layout = QVBoxLayout(w)

        # --- Language Settings ---
        lang_group = QGroupBox(self.translator.tr("language"))
        lang_layout = QFormLayout(lang_group)

        self.language_combo = QComboBox() # Language selection
        self.language_combo.addItem("Polski", "pl") # Do not translate the language name itself
        self.language_combo.addItem("English", "en")
        
        # Set current language based on config
        current_lang_idx = self.language_combo.findData(self.config.get("language", "pl"))
        if current_lang_idx != -1:
            self.language_combo.setCurrentIndex(current_lang_idx)

        apply_lang_btn = QPushButton(self.translator.tr("apply_and_restart")) # Apply button
        apply_lang_btn.clicked.connect(self.apply_language_settings)

        lang_layout.addRow(self.translator.tr("select_language"), self.language_combo)
        lang_layout.addRow(apply_lang_btn)
        layout.addWidget(lang_group)

        # --- Shortcuts Display (read-only for now) ---
        shortcuts_group = QGroupBox(self.translator.tr("shortcuts"))
        shortcuts_layout = QVBoxLayout(shortcuts_group)

        self.shortcuts_table = QTableWidget()
        self.shortcuts_table.setColumnCount(2)
        self.shortcuts_table.setHorizontalHeaderLabels([self.translator.tr("action"), self.translator.tr("shortcut")]) # Table headers
        self.shortcuts_table.horizontalHeader().setStretchLastSection(True)
        self.shortcuts_table.setEditTriggers(QAbstractItemView.DoubleClicked)
        self.populate_shortcuts_table()

        shortcuts_layout.addWidget(self.shortcuts_table)

        save_shortcuts_btn = QPushButton(self.translator.tr("save_shortcuts_button"))
        save_shortcuts_btn.clicked.connect(self.save_shortcuts)
        shortcuts_layout.addWidget(save_shortcuts_btn)

        layout.addWidget(shortcuts_group)

        # --- Import/Export Settings ---
        imex_group = QGroupBox(self.translator.tr("import_export_title"))
        imex_layout = QHBoxLayout(imex_group)

        import_btn = QPushButton(self.translator.tr("import_button"))
        import_btn.clicked.connect(self.import_configuration)

        export_btn = QPushButton(self.translator.tr("export_button"))
        export_btn.clicked.connect(self.export_configuration)

        imex_layout.addWidget(import_btn)
        imex_layout.addWidget(export_btn)
        layout.addWidget(imex_group)

        # --- Autostart Settings ---
        autostart_group = QGroupBox(self.translator.tr("autostart_title"))
        autostart_layout = QVBoxLayout(autostart_group)
        self.autostart_checkbox = QCheckBox(self.translator.tr("autostart_checkbox"))
        
        autostart_path = Path.home() / ".config/autostart/radio-scheduler.desktop"
        self.autostart_checkbox.setChecked(autostart_path.exists())
        self.autostart_checkbox.stateChanged.connect(self.handle_autostart_change)
        
        autostart_layout.addWidget(self.autostart_checkbox)
        autostart_layout.addWidget(QLabel(self.translator.tr("autostart_description")))
        
        layout.addWidget(autostart_group)


        layout.addStretch()
        return w

    def populate_shortcuts_table(self):
        """Fills the shortcuts table with data from the configuration."""
        self.shortcuts_table.setRowCount(0) # Clear existing rows
        for action_name, shortcut_key in self.config["shortcuts"].items():
            row_position = self.shortcuts_table.rowCount()
            self.shortcuts_table.insertRow(row_position)
            
            action_item = QTableWidgetItem(action_name)
            action_item.setFlags(action_item.flags() & ~Qt.ItemIsEditable) # Make action column read-only
            self.shortcuts_table.setItem(row_position, 0, action_item)
            self.shortcuts_table.setItem(row_position, 1, QTableWidgetItem(shortcut_key))

    def apply_language_settings(self):
        """Saves the selected language and prompts the user to restart the application."""
        selected_lang = self.language_combo.currentData()
        self.config["language"] = selected_lang
        try:
            with open(CONFIG_PATH, "w", encoding="utf-8") as f:
                yaml.safe_dump(self.config, f, allow_unicode=True, sort_keys=False) # Save the new language setting

            reply = QMessageBox.question(self, self.translator.tr("app_restart_prompt"),
                                         self.translator.tr("language_change_prompt"),
                                         QMessageBox.Yes | QMessageBox.No, QMessageBox.No)

            if reply == QMessageBox.Yes:
                subprocess.Popen([sys.executable] + sys.argv)
                self.is_restarting = True
                QApplication.quit()
        except Exception as e:
            QMessageBox.critical(self, self.translator.tr("save_error"), self.translator.tr("lang_config_save_error", e=e))

    def handle_autostart_change(self, state):
        """Creates or removes the .desktop file for autostart."""
        autostart_dir = Path.home() / ".config/autostart"
        desktop_file_path = autostart_dir / "radio-scheduler.desktop"

        if state == Qt.Checked:
            try:
                autostart_dir.mkdir(parents=True, exist_ok=True)
                
                # Find the executable path. `shutil.which` is the most reliable way for installed packages.
                import shutil
                executable_path = shutil.which("radio-scheduler-gui")
                if not executable_path:
                    # Fallback for running directly from source code
                    executable_path = f"{sys.executable} {Path(__file__).resolve()}"

                desktop_content = f"""[Desktop Entry]
Name=RadioScheduler
Comment={self.translator.tr("autostart_comment")}
Exec={executable_path} --hidden
Icon={ICON_PATH.resolve()}
Terminal=false
Type=Application
Categories=AudioVideo;Audio;Player;
"""
                desktop_file_path.write_text(desktop_content, encoding="utf-8")
            except Exception as e:
                logging.error(f"Error creating autostart file: {e}")
        elif desktop_file_path.exists():
            desktop_file_path.unlink()

    def save_shortcuts(self):
        """Saves the edited shortcuts from the table to the config and prompts for a restart."""
        new_shortcuts = {}
        for row in range(self.shortcuts_table.rowCount()):
            action_name = self.shortcuts_table.item(row, 0).text()
            shortcut_key = self.shortcuts_table.item(row, 1).text()
            
            # Validate the key sequence
            if not QKeySequence.fromString(shortcut_key):
                QMessageBox.warning(self, self.translator.tr("error"), self.translator.tr("invalid_shortcut_error", shortcut=shortcut_key))
                return
            
            new_shortcuts[action_name] = shortcut_key
        
        self.config["shortcuts"] = new_shortcuts
        
        try:
            with open(CONFIG_PATH, "w", encoding="utf-8") as f:
                yaml.safe_dump(self.config, f, allow_unicode=True, sort_keys=False)
            
            self.apply_language_settings() # Reuse the restart logic
        except Exception as e:
            QMessageBox.critical(self, self.translator.tr("save_error"), self.translator.tr("config_save_error", e=e))

    def export_configuration(self):
        """Exports the current configuration to a user-selected YAML file."""
        file_path, _ = QFileDialog.getSaveFileName(self, self.translator.tr("export_dialog_title"),
                                                   str(Path.home() / "radio-scheduler-backup.yaml"),
                                                   "YAML Files (*.yaml *.yml)")
        if file_path:
            try:
                with open(file_path, 'w', encoding='utf-8') as f:
                    yaml.safe_dump(self.config, f, allow_unicode=True, sort_keys=False)
                QMessageBox.information(self, self.translator.tr("export_success_title"),
                                        self.translator.tr("export_success_text", path=file_path))
            except Exception as e:
                QMessageBox.critical(self, self.translator.tr("save_error"),
                                     self.translator.tr("export_error_text", e=e))

    def import_configuration(self):
        """Imports a configuration from a user-selected YAML file."""
        file_path, _ = QFileDialog.getOpenFileName(self, self.translator.tr("import_dialog_title"),
                                                   str(Path.home()),
                                                   "YAML Files (*.yaml *.yml)")
        if file_path:
            reply = QMessageBox.question(self, self.translator.tr("import_confirm_title"),
                                         self.translator.tr("import_confirm_text", path=file_path),
                                         QMessageBox.Yes | QMessageBox.No, QMessageBox.No)

            if reply == QMessageBox.Yes:
                try:
                    with open(file_path, 'r', encoding='utf-8') as f:
                        new_config_content = f.read()
                        # Validate that it's valid YAML before overwriting
                        yaml.safe_load(new_config_content)

                    # Overwrite the main config file
                    with open(CONFIG_PATH, 'w', encoding='utf-8') as f:
                        f.write(new_config_content)

                    # Restart the application
                    subprocess.Popen([sys.executable] + sys.argv)
                    self.is_restarting = True
                    QApplication.quit()
                except Exception as e:
                    QMessageBox.critical(self, self.translator.tr("import_error_title"),
                                         self.translator.tr("import_error_text", e=e))

app = QApplication(sys.argv)
app.setQuitOnLastWindowClosed(False)
if ICON_PATH.exists():
    app.setWindowIcon(QIcon(str(ICON_PATH)))

def main():
    win = MainWindow()
    win.update_tray_icon()
    if "--hidden" not in sys.argv:
        win.show()
    sys.exit(app.exec())

if __name__ == "__main__":
    try:
        main()
    except Exception as e:
        logging.critical("Aplikacja GUI napotkała nieobsługiwany błąd.", exc_info=True)
