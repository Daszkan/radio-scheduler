#!/usr/bin/env python3
# Copyright (c) 2025 - 2026 Daszkan (Jacek S.)
#
# This software is released under the MIT License.
# https://opensource.org/licenses/MIT
import sys
import yaml
import subprocess
from pathlib import Path
from datetime import time, datetime
from logging.handlers import RotatingFileHandler
from collections import defaultdict
from datetime import timedelta
import logging, os
import configparser
import shutil
import zipfile
import argparse

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
    QInputDialog,
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
    QProgressBar,
    QRadioButton,
    QSlider,
    QSpinBox,
    QStyle,
    QStackedWidget,
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
from PySide6.QtCore import QEvent, Qt, QTimer, QUrl, QByteArray, QRectF, QPoint
from PySide6.QtNetwork import QNetworkAccessManager, QNetworkRequest, QNetworkReply
from PySide6.QtGui import QAction, QDesktopServices, QIcon, QFont, QKeySequence, QShortcut, QPalette, QPainter, QPixmap, QColor, QBrush, QLinearGradient, QPolygon
from PySide6.QtSvg import QSvgRenderer

# --- Global Paths and Configuration ---
CONFIG_PATH = Path.home() / ".config/radio-scheduler/config.yaml"
LOG_PATH = Path.home() / ".config/radio-scheduler/radio-scheduler-gui.log"
DAEMON_PATH = Path(__file__).parent / "radio-scheduler.py"
MANUAL_OVERRIDE_LOCK = Path.home() / ".config/radio-scheduler/manual_override.lock"
NO_NEWS_TODAY_LOCK = Path.home() / ".config/radio-scheduler/no-news-today"
ICONS_PATH = Path.home() / ".config/radio-scheduler/icons"
ICON_PATH = Path(__file__).parent / "app_icon.png"

# Konfiguracja logowania z rotacją plików
LOG_PATH.parent.mkdir(parents=True, exist_ok=True)
log_formatter = logging.Formatter('%(asctime)s - %(levelname)s - %(message)s')
log_handler = RotatingFileHandler(LOG_PATH, maxBytes=1024*1024, backupCount=5, encoding='utf-8')
log_handler.setFormatter(log_formatter)

logger = logging.getLogger()
logger.setLevel(logging.INFO) # Zmieniono poziom logowania na INFO
logger.addHandler(log_handler)

# Definicje ikon SVG (zintegrowane, aby nie polegać na zewnętrznym skrypcie)
SVG_ICONS = {
    "play.svg": '''<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="#333"><path d="M8 5v14l11-7z"/></svg>''',
    "stop.svg": '''<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="#333"><path d="M6 6h12v12H6z"/></svg>''',
    "volume.svg": '''<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="#333"><path d="M3 9v6h4l5 5V4L7 9H3zm13.5 3c0-1.77-1.02-3.29-2.5-4.03v8.05c1.48-.73 2.5-2.25 2.5-4.02zM14 3.23v2.06c2.89.86 5 3.54 5 6.71s-2.11 5.85-5 6.71v2.06c4.01-.91 7-4.49 7-8.77s-2.99-7.86-7-8.77z"/></svg>''',
    "clock.svg": '''<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="none" stroke="#333" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><circle cx="12" cy="12" r="10"/><polyline points="12 6 12 12 16 14"/></svg>''',
    "reload.svg": '''<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="#333"><path d="M17.65 6.35C16.2 4.9 14.21 4 12 4c-4.42 0-7.99 3.58-7.99 8s3.57 8 7.99 8c3.73 0 6.84-2.55 7.73-6h-2.08c-.82 2.33-3.04 4-5.65 4-3.31 0-6-2.69-6-6s2.69-6 6-6c1.66 0 3.14.69 4.22 1.78L13 11h7V4l-2.35 2.35z"/></svg>''',
    "settings.svg": '''<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="#333"><path d="M3 17v2h6v-2H3zM3 5v2h10V5H3zm10 16v-2h8v-2h-8v-2h-2v6h2zM7 9v2H3v2h4v2h2V9H7zm14 4v-2H11v2h10zm-6-4h2V7h4V5h-4V3h-2v6z"/></svg>''',
    "exit.svg": '''<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="#333"><path d="M10.09 15.59L11.5 17l5-5-5-5-1.41 1.41L12.67 11H3v2h9.67l-2.58 2.59zM19 3H5c-1.11 0-2 .9-2 2v4h2V5h14v14H5v-4H3v4c0 1.1.89 2 2 2h14c1.1 0 2-.9 2-2V5c0-1.1-.9-2-2-2z"/></svg>''',
    "manual.svg": '''<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="#333"><path d="M20.5 11H19V5h-2v4h-2V3h-2v4h-2V5H9v6H7.5c-.83 0-1.5.67-1.5 1.5v4c0 .83.67 1.5 1.5 1.5H16v-1.5c0-.83-.67-1.5-1.5-1.5H13v-2.5h1.5c.83 0 1.5-.67 1.5-1.5V11h4.5c.83 0 1.5-.67 1.5-1.5v-4c0-.83-.67-1.5-1.5-1.5s-1.5.67-1.5 1.5v2.5z"/></svg>''',
    "check.svg": '''<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="#4CAF50"><path d="M9 16.17L4.83 12l-1.42 1.41L9 19 21 7l-1.41-1.41z"/></svg>''',
    "error.svg": '''<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="#F44336"><path d="M19 6.41L17.59 5 12 10.59 6.41 5 5 6.41 10.59 12 5 17.59 6.41 19 12 13.41 17.59 19 19 17.59 13.41 12z"/></svg>'''
}

def ensure_icons_exist():
    """Generates default SVG icons if they don't exist."""
    try:
        ICONS_PATH.mkdir(parents=True, exist_ok=True)
        for name, content in SVG_ICONS.items():
            file_path = ICONS_PATH / name
            if not file_path.exists():
                with open(file_path, "w", encoding="utf-8") as f:
                    f.write(content)
    except Exception as e:
        logger.error(f"Failed to generate icons: {e}")

def get_icon(name, fallback_enum=None):
    """Loads an icon from the icons directory, adapting color to theme."""
    if ICONS_PATH.exists():
        icon_path = ICONS_PATH / f"{name}.svg"
        if icon_path.exists():
            try:
                with open(icon_path, 'r', encoding='utf-8') as f:
                    svg_data = f.read()
                
                # Dynamiczne kolorowanie dla ikon monochromatycznych
                if name not in ['check', 'error']:
                    col = QApplication.palette().color(QPalette.ColorGroup.Active, QPalette.ColorRole.Text).name()
                    svg_data = svg_data.replace('#333', col)
                
                renderer = QSvgRenderer(QByteArray(svg_data.encode('utf-8')))
                icon = QIcon()
                for size in [16, 24, 32, 48, 64, 96]:
                    pixmap = QPixmap(size, size)
                    pixmap.fill(Qt.transparent)
                    painter = QPainter(pixmap)
                    renderer.render(painter)
                    painter.end()
                    icon.addPixmap(pixmap)
                return icon
            except Exception as e:
                logger.error(f"Failed to load/render icon {name}: {e}")

    if fallback_enum is not None:
        return QApplication.style().standardIcon(fallback_enum)
    return QIcon()

class AnalogClock(QWidget):
    """A simple analog clock widget."""
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setMinimumSize(200, 200) # Allow resizing but keep reasonable min size
        self.timer = QTimer(self)
        self.timer.timeout.connect(self.update)
        self.timer.start(1000)

    def paintEvent(self, event):
        side = min(self.width(), self.height())
        time = datetime.now().time()

        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)
        painter.translate(self.width() / 2, self.height() / 2)
        painter.scale(side / 200.0, side / 200.0)

        # Hands
        hour_hand = QPolygon([QPoint(7, 8), QPoint(-7, 8), QPoint(0, -50)])
        minute_hand = QPolygon([QPoint(7, 8), QPoint(-7, 8), QPoint(0, -80)])
        second_hand = QPolygon([QPoint(1, 8), QPoint(-1, 8), QPoint(0, -90)])

        # Colors from theme
        hour_color = self.palette().color(QPalette.ColorRole.Text)
        minute_color = self.palette().color(QPalette.ColorRole.Text)
        second_color = QColor(Qt.red)

        # Draw hour hand
        painter.save()
        painter.setPen(Qt.NoPen)
        painter.setBrush(hour_color)
        painter.rotate(30.0 * (time.hour + time.minute / 60.0))
        painter.drawConvexPolygon(hour_hand)
        painter.restore()

        # Draw minute hand
        painter.save()
        painter.setPen(Qt.NoPen)
        painter.setBrush(minute_color)
        painter.rotate(6.0 * (time.minute + time.second / 60.0))
        painter.drawConvexPolygon(minute_hand)
        painter.restore()
        
        # Draw second hand
        painter.save()
        painter.setPen(Qt.NoPen)
        painter.setBrush(second_color)
        painter.rotate(6.0 * time.second)
        painter.drawConvexPolygon(second_hand)
        painter.restore()

        # Draw clock face
        painter.setPen(hour_color)
        for i in range(12):
            painter.drawLine(88, 0, 96, 0)
            painter.rotate(30.0)

        # Draw center point
        painter.setPen(Qt.NoPen)
        painter.setBrush(second_color)
        painter.drawEllipse(-3, -3, 6, 6)

class DigitalClock(QWidget):
    """A simple digital clock widget."""
    def __init__(self, parent=None):
        super().__init__(parent)
        layout = QVBoxLayout(self)
        layout.setAlignment(Qt.AlignCenter)
        layout.setContentsMargins(0, 20, 0, 20)
        
        self.clock_label = QLabel()
        self.clock_label.setAlignment(Qt.AlignCenter)
        font = QFont()
        font.setPointSize(48)
        font.setBold(True)
        self.clock_label.setFont(font)
        layout.addWidget(self.clock_label)
        
        self.timer = QTimer(self)
        self.timer.timeout.connect(self.update_time)
        self.timer.start(1000)
        self.update_time()

    def update_time(self):
        self.clock_label.setText(datetime.now().strftime("%H:%M:%S"))

class ScheduleInfoWidget(QWidget):
    """A widget showing date and next scheduled event."""
    def __init__(self, main_window, parent=None):
        super().__init__(parent)
        self.mw = main_window
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 10, 0, 10)
        
        # Next Event Container
        self.next_event_group = QGroupBox()
        self.next_event_group.setAlignment(Qt.AlignCenter)
        vbox = QVBoxLayout(self.next_event_group)
        
        self.next_station_label = QLabel("--")
        self.next_station_label.setAlignment(Qt.AlignCenter)
        self.next_station_label.setStyleSheet("font-size: 16px; font-weight: bold;")
        
        self.countdown_label = QLabel("--")
        self.countdown_label.setAlignment(Qt.AlignCenter)
        self.countdown_label.setStyleSheet("color: #555;")
        
        vbox.addWidget(self.next_station_label)
        vbox.addWidget(self.countdown_label)
        
        # News Label
        self.news_label = QLabel()
        self.news_label.setAlignment(Qt.AlignCenter)
        self.news_label.setStyleSheet("color: #2196F3; font-weight: bold; margin-top: 5px;")

        # Return Button
        self.return_btn = QPushButton()
        self.return_btn.setIcon(get_icon("reload", QStyle.StandardPixmap.SP_BrowserReload))
        self.return_btn.clicked.connect(self.mw.return_to_schedule)
        self.return_btn.setStyleSheet("background-color: #f44336; color: white; font-weight: bold; padding: 6px; border-radius: 4px;")
        self.return_btn.hide()
        
        # Date
        self.date_label = QLabel()
        self.date_label.setAlignment(Qt.AlignCenter)
        self.date_label.setStyleSheet("color: #666; font-size: 16px; font-weight: bold;")
        layout.addWidget(self.date_label)

        layout.addSpacing(15)
        layout.addWidget(self.next_event_group)
        layout.addWidget(self.news_label)
        layout.addWidget(self.return_btn)
        
        self.timer = QTimer(self)
        self.timer.timeout.connect(self.update_state)
        self.timer.start(1000)
        
        self.update_state()

    def update_state(self):
        now = datetime.now()
        # Format daty zależny od locale byłby lepszy, ale tutaj uprościmy
        self.date_label.setText(now.strftime("%Y-%m-%d"))
        
        # Update translations
        self.next_event_group.setTitle(self.mw.translator.tr("next_schedule_event"))
        self.return_btn.setText(self.mw.translator.tr("return_to_schedule"))

        # Find next event
        next_rule = self.find_next_rule(now)

        # Show "Return to schedule" button only if manual override is active AND there's a schedule to return to.
        # A schedule is active if there's a next rule OR a default station is set.
        has_active_schedule = next_rule is not None or self.mw.schedule.get("default")
        if MANUAL_OVERRIDE_LOCK.exists() and has_active_schedule:
            self.return_btn.show()
        else:
            self.return_btn.hide()

        if next_rule:
            self.next_station_label.setText(f"{next_rule['station']}")
            # Calculate countdown
            target_time = datetime.combine(now.date(), time.fromisoformat(next_rule['from']))
            delta = target_time - now
            minutes = int(delta.total_seconds() / 60)
            self.countdown_label.setText(self.mw.translator.tr("event_in", time=next_rule['from'], min=minutes))
        else:
            self.next_station_label.setText(self.mw.translator.tr("no_events_today"))
            self.countdown_label.setText("")

        # Find next news
        next_news = self.find_next_news(now)
        if next_news:
            self.news_label.setText(self.mw.translator.tr("next_news", time=next_news.strftime("%H:%M")))
            self.news_label.show()
        else:
            self.news_label.hide()

    def find_next_rule(self, now):
        """Finds the next scheduled rule for today."""
        weekday_map = {0: "mon", 1: "tue", 2: "wed", 3: "thu", 4: "fri", 5: "sat", 6: "sun"}
        current_day_code = weekday_map[now.weekday()]
        current_time_str = now.strftime("%H:%M")
        
        rules = self.mw.schedule.get("weekly", [])
        candidates = []
        
        for rule in rules:
            if current_day_code in rule.get("days", []):
                if rule["from"] > current_time_str:
                    candidates.append(rule)
        
        candidates.sort(key=lambda x: x["from"])
        return candidates[0] if candidates else None

    def find_next_news(self, now):
        if NO_NEWS_TODAY_LOCK.exists() and NO_NEWS_TODAY_LOCK.read_text().strip() == str(now.date()):
            return None
            
        news_cfg = self.mw.schedule.get("news_breaks", {})
        if not news_cfg.get("enabled", True):
            return None

        offset = news_cfg.get("start_minute_offset", 0)
        candidates = []
        
        weekday_map = {0: "mon", 1: "tue", 2: "wed", 3: "thu", 4: "fri", 5: "sat", 6: "sun"}
        weekday = weekday_map[now.weekday()]

        # Helper to process rules
        def process_rule(rule):
            try:
                start = datetime.strptime(rule.get("from", "00:00"), "%H:%M").time()
                end = datetime.strptime(rule.get("to", "22:00"), "%H:%M").time()
                interval = rule.get("interval_minutes", 60)
                
                curr = datetime.combine(now.date(), start)
                end_dt = datetime.combine(now.date(), end)
                
                while curr <= end_dt:
                    trigger_dt = curr + timedelta(minutes=offset)
                    if trigger_dt > now and trigger_dt.time() <= end:
                         candidates.append(trigger_dt)
                    curr += timedelta(minutes=interval)
            except Exception as e:
                logger.error(f"Error processing news rule in dashboard: {e}", exc_info=True)

        if news_cfg.get("use_advanced", False):
            for rule in news_cfg.get("advanced", []):
                if weekday in rule.get("days", []):
                    process_rule(rule)
        else:
            simple = news_cfg.get("simple", {})
            # Fix: Default to all days if missing (matches daemon logic)
            days = simple.get("days", ["mon", "tue", "wed", "thu", "fri", "sat", "sun"])
            if weekday in days and simple.get("station"):
                process_rule(simple)

        if candidates:
            candidates.sort()
            return candidates[0]
        return None

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
        logger.error(f"Błąd podczas ręcznego odtwarzania stacji {station.get('name', '')}: {e}")
        # This function is called from outside MainWindow, so we can't use self.translator
        # A simple message box is sufficient.
        QMessageBox.critical(None, "Playback Error", f"Could not play station. Check logs:\n{LOG_PATH}")

def find_mpd_conf_path():
    """
    Searches for the mpd.conf file in common user locations in order of precedence.
    1. $XDG_CONFIG_HOME/mpd/mpd.conf (e.g., ~/.config/mpd/mpd.conf)
    2. ~/.mpd/mpd.conf
    3. ~/.mpdconf
    Returns the first path found, or the default XDG path if none exist.
    """
    home = Path.home()
    # Path 1: XDG standard
    xdg_config_home = Path(os.environ.get("XDG_CONFIG_HOME", home / ".config"))
    path1 = xdg_config_home / "mpd/mpd.conf"
    # Other common paths
    path2 = home / ".mpd/mpd.conf"
    path3 = home / ".mpdconf"

    for path in [path1, path2, path3]:
        if path.exists():
            return path
    # If no file is found, return the preferred (XDG) path for creation.
    return path1
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
        self.app_name_label = QLabel("RadioScheduler v1.2")
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

        # --- Scheduler Status ---
        self.scheduler_group = QGroupBox(self.translator.tr("scheduler_status_title"))
        scheduler_layout = QHBoxLayout(self.scheduler_group)
        self.scheduler_status_icon = QLabel()
        self.scheduler_status_label = QLabel()
        scheduler_layout.addWidget(self.scheduler_status_icon)
        scheduler_layout.addWidget(self.scheduler_status_label)
        scheduler_layout.addStretch()
        main_layout.addWidget(self.scheduler_group)

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
        log_path_layout = self.create_path_widget(LOG_PATH, allow_open_file=True, allow_clear=True)

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
        env_layout.addRow(self.translator.tr("qt_license_label"), QLabel("LGPLv3"))
        
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

    def create_path_widget(self, path, allow_open_file=False, allow_clear=False):
        layout = QHBoxLayout()
        line_edit = QLineEdit(str(path))
        line_edit.setReadOnly(True)
        layout.addWidget(line_edit)

        if allow_open_file:
            open_file_btn = QPushButton(self.translator.tr("open_file"))
            open_file_btn.clicked.connect(lambda: QDesktopServices.openUrl(QUrl.fromLocalFile(str(path))))
            layout.addWidget(open_file_btn)

        if allow_clear:
            clear_btn = QPushButton(self.translator.tr("clear_logs"))
            clear_btn.clicked.connect(lambda: self.clear_log_file(path))
            layout.addWidget(clear_btn)

        button = QPushButton(self.translator.tr("open_dir"))
        button.clicked.connect(lambda: self.open_directory(path.parent))
        layout.addWidget(button)
        return layout

    def clear_log_file(self, path):
        """Clears the content of the specified log file."""
        if QMessageBox.question(self, self.translator.tr("delete_prompt"),
                                self.translator.tr("clear_logs_confirm", path=path)) != QMessageBox.Yes:
            return

        try:
            # Jeśli czyścimy log bieżącej aplikacji, musimy to zrobić przez handler loggera,
            # aby uniknąć problemów z otwartym uchwytem pliku (np. zapisywania null-bytes).
            if path.resolve() == LOG_PATH.resolve():
                root_logger = logging.getLogger()
                for h in root_logger.handlers:
                    if hasattr(h, 'baseFilename') and Path(h.baseFilename).resolve() == path.resolve():
                        h.acquire()
                        try:
                            if h.stream:
                                h.stream.seek(0)
                                h.stream.truncate(0)
                        finally:
                            h.release()
            else:
                # Dla innych plików po prostu nadpisujemy pustą treścią
                with open(path, 'w', encoding='utf-8'):
                    pass
            
            QMessageBox.information(self, self.translator.tr("success"), self.translator.tr("logs_cleared"))
        except Exception as e:
            QMessageBox.critical(self, self.translator.tr("error"), str(e))

    def open_directory(self, path):
        """Opens the specified directory in the default file manager."""
        QDesktopServices.openUrl(f"file:///{path}")

    def retranslate_ui(self):
        # This method is now only for text translation, not logic
        self.scheduler_group.setTitle(self.translator.tr("scheduler_status_title"))
        self.stats_group.setTitle(self.translator.tr("mpd_stats_title"))
        self.instr_group.setTitle(self.translator.tr("mpd_install_title"))
        # The content of the labels is set in update_content

    def update_content(self):
        """Fetches dynamic data (like MPD status) and updates the UI content."""
        # Check Scheduler Daemon
        is_scheduler_running = subprocess.call(["pgrep", "-f", "radio-scheduler.py"], stdout=subprocess.DEVNULL) == 0
        if is_scheduler_running:
            self.scheduler_status_label.setText(self.translator.tr("scheduler_status_active"))
            self.scheduler_status_icon.setPixmap(get_icon("check", QStyle.StandardPixmap.SP_DialogApplyButton).pixmap(16, 16))
        else:
            self.scheduler_status_label.setText(self.translator.tr("scheduler_status_inactive"))
            self.scheduler_status_icon.setPixmap(get_icon("error", QStyle.StandardPixmap.SP_DialogCancelButton).pixmap(16, 16))

        is_mpd_running = subprocess.call(["pgrep", "-f", "mpd"], stdout=subprocess.DEVNULL) == 0
        if is_mpd_running:
            self.mpd_status_label.setText(self.translator.tr("mpd_status_active"))
            self.mpd_status_icon.setPixmap(get_icon("check", QStyle.StandardPixmap.SP_DialogApplyButton).pixmap(16, 16))
            self.stats_group.setVisible(True)
            self.instr_group.setChecked(False)
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
                logger.error(f"Error updating 'About' tab content: {e}")
                self.stats_group.setVisible(False)
        else:
            self.mpd_status_label.setText(self.translator.tr("mpd_status_inactive"))
            self.mpd_status_icon.setPixmap(get_icon("error", QStyle.StandardPixmap.SP_DialogCancelButton).pixmap(16, 16))
            self.stats_group.setVisible(False)
            self.instr_group.setChecked(True)
            self.instr_group.setVisible(True) # Show instructions if MPD is not running

class MainWindow(QMainWindow):
    """The main application window."""
    def __init__(self):
        super().__init__()
        self.last_known_song = None # Bufor dla aktualnie granego utworu
        self.is_restarting = False # Flaga do obsługi restartu
        self.manual_override_status = MANUAL_OVERRIDE_LOCK.exists() # Śledzenie stanu blokady dla powiadomień
        self.previous_volume = 50 # Zapamiętana głośność przed wyciszeniem
        
        self.nam = QNetworkAccessManager(self) # Menedżer sieci do testowania URL
        self.sleep_timer = QTimer(self) # Timer dla wyłącznika czasowego
        self.sleep_timer.timeout.connect(self.on_sleep_timer_triggered)
        self.sleep_timer_end_time = None

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
        self.tab_player_widget = self.tab_player()
        self.tab_stations_widget = self.tab_stations()
        self.tab_schedule_widget = self.tab_schedule()
        self.tab_news_widget = self.tab_news()
        self.about_tab = AboutTab(self)
        self.tab_settings_widget = self.tab_settings()
        self.tab_mpd_config_widget = self.tab_mpd_config()

        self.tabs.insertTab(0, self.tab_player_widget, "") # Wstaw jako pierwszą
        self.tabs.addTab(self.tab_stations_widget, "")
        self.tabs.addTab(self.tab_schedule_widget, "")
        self.tabs.addTab(self.tab_news_widget, "")
        self.tabs.addTab(self.tab_settings_widget, "")
        self.tabs.addTab(self.tab_mpd_config_widget, "")
        self.tabs.addTab(self.about_tab, "")

        self.setCentralWidget(self.tabs)

        # Odroczone pierwsze odświeżenie UI, aby uniknąć problemów z timingiem przy starcie
        QTimer.singleShot(0, self.initial_ui_refresh)

        # Tłumaczenia są ładowane na końcu, po utworzeniu wszystkich widgetów
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

        self.no_news_today_action = QAction(self)
        self.no_news_today_action.setCheckable(True)
        self.no_news_today_action.triggered.connect(self.toggle_no_news_today)

        self.restart_daemon_action = QAction(self)
        self.restart_daemon_action.triggered.connect(self.restart_scheduler_daemon)
        self.addAction(self.restart_daemon_action)

        # Akcje dla odtwarzacza
        self.play_action = QAction(self)
        self.play_action.triggered.connect(lambda: mpc.play())
        self.addAction(self.play_action)

        self.stop_action = QAction(self)
        self.stop_action.triggered.connect(lambda: mpc.stop())
        self.addAction(self.stop_action)

    def create_tray_icon(self):
        """Creates and configures the system tray icon and its menu."""
        self.tray = QSystemTrayIcon(get_icon("play", QStyle.StandardPixmap.SP_MediaPlay), self)
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
        icon_name = "manual" if MANUAL_OVERRIDE_LOCK.exists() else "play"
        fallback = QStyle.StandardPixmap.SP_MediaSeekForward if MANUAL_OVERRIDE_LOCK.exists() else QStyle.StandardPixmap.SP_MediaPlay
        icon = get_icon(icon_name, fallback)
        self.tray.setIcon(icon)

    def build_tray_menu(self):
        """Builds or rebuilds the context menu for the system tray icon."""
        menu = QMenu()
        style = QApplication.style() # Use app style, it's safer
        current_url = self.last_known_song # Use buffered value
        favorites = [s for s in self.config.get("stations", []) if s.get("favorite")]

        self.tray_now_playing_action = menu.addAction(self.translator.tr("now_playing", current="..."))
        self.tray_now_playing_action.setIcon(style.standardIcon(QStyle.StandardPixmap.SP_MediaPlay))
        self.tray_now_playing_action.setEnabled(False)
        menu.addSeparator() # Separator for favorites

        if favorites:
            for s in favorites:
                a = menu.addAction(s['name'])
                a.setIcon(style.standardIcon(QStyle.StandardPixmap.SP_MediaPlay)) # Użyj istniejącej ikony
                a.triggered.connect(lambda _, x=s: (play_now(x), self.now_playing_label.setText(self.translator.tr("now_playing", current=x["name"])), self.update_return_to_schedule_button()))
                if s['url'] == current_url:
                    font = a.font()
                    font.setBold(True)
                    a.setFont(font)
        else:
            no_fav_action = menu.addAction(self.translator.tr("no_favorites"))
            no_fav_action.setIcon(style.standardIcon(QStyle.StandardPixmap.SP_MediaPlay)) # Użyj istniejącej ikony
            no_fav_action.setEnabled(False)

        menu.addSeparator() # Separator for volume

        self.tray_vol_menu = menu.addMenu(self.translator.tr("volume_menu", volume=0))
        self.tray_vol_menu.setIcon(style.standardIcon(QStyle.StandardPixmap.SP_MediaVolume))
        for v in range(0, 101, 5):
            a = self.tray_vol_menu.addAction(f"{v:3}%")
            a.triggered.connect(lambda _, vol=v: (mpc.set_volume(vol), self.build_tray_menu()))

        menu.addSeparator()

        # --- Sleep Timer Menu ---
        st_title = self.translator.tr("sleep_timer")
        if self.sleep_timer_end_time:
            remaining = int((self.sleep_timer_end_time - datetime.now()).total_seconds() / 60) + 1
            st_title = self.translator.tr("sleep_timer_menu", remaining=remaining)
        
        sleep_menu = menu.addMenu(st_title)
        sleep_menu.setIcon(get_icon("clock", QStyle.StandardPixmap.SP_MediaStop))
        
        a_off = sleep_menu.addAction(self.translator.tr("sleep_timer_off"))
        a_off.setCheckable(True)
        a_off.setChecked(self.sleep_timer_end_time is None)
        a_off.triggered.connect(lambda: self.set_sleep_timer(0))
        sleep_menu.addSeparator()
        for m in [15, 30, 45, 60, 90, 120]:
            sleep_menu.addAction(self.translator.tr("sleep_in_min", min=m), lambda min=m: self.set_sleep_timer(min))
        sleep_menu.addSeparator()
        sleep_menu.addAction(self.translator.tr("sleep_custom"), self.set_custom_sleep_timer)
        
        menu.addSeparator()

        if MANUAL_OVERRIDE_LOCK.exists():
            return_action = menu.addAction(self.translator.tr("return_to_schedule"))
            return_action.setIcon(get_icon("reload", QStyle.StandardPixmap.SP_BrowserReload))
            return_action.triggered.connect(self.return_to_schedule)
            menu.addSeparator()

        # Opcja wyłączenia wiadomości
        is_disabled = NO_NEWS_TODAY_LOCK.exists() and NO_NEWS_TODAY_LOCK.read_text().strip() == str(datetime.now().date())
        self.no_news_today_action.setChecked(is_disabled)
        menu.addAction(self.no_news_today_action)

        self.restart_daemon_action.setIcon(get_icon("reload", QStyle.StandardPixmap.SP_BrowserReload))
        menu.addAction(self.restart_daemon_action)
        menu.addSeparator() # Separator before show/quit
        menu.addAction(get_icon("settings", QStyle.StandardPixmap.SP_DesktopIcon), self.translator.tr("show_editor"), self.show)
        menu.addAction(get_icon("exit", QStyle.StandardPixmap.SP_DialogCloseButton), self.translator.tr("exit"), clear_and_exit)
        
        self.tray.setContextMenu(menu)
        self.update_dynamic_tray_elements() # Initial update
        # Przetłumacz nową akcję po jej utworzeniu
        self.no_news_today_action.setText(self.translator.tr("disable_news_today"))

    def update_tray_tooltip(self):
        """Updates the tooltip for the tray icon with current status."""
        current = mpc.get_current()
        vol = mpc.get_volume()
        self.tray.setToolTip(f"RadioScheduler\n{self.translator.tr('now_playing', current=current)}\n{self.translator.tr('volume_menu', volume=vol)}")
    
    def update_dynamic_tray_elements(self):
        """Updates parts of the tray menu that change, like volume and current song."""
        if hasattr(self, 'tray_vol_menu'):
            self.tray_vol_menu.setTitle(self.translator.tr("volume_menu", volume=mpc.get_volume() or 0))
        if hasattr(self, 'tray_now_playing_action'):
            self.tray_now_playing_action.setText(self.translator.tr("now_playing", current=mpc.get_current()))

        # Aktualizacja tytułu menu Sleep Timer (jeśli jest otwarte lub przy następnym otwarciu)
        # Wymagałoby to przebudowy menu co minutę, co robimy w on_timer_tick pośrednio

    def set_sleep_timer(self, minutes):
        """Sets or disables the sleep timer."""
        if minutes <= 0:
            self.sleep_timer.stop()
            self.sleep_timer_end_time = None
        else:
            self.sleep_timer.setSingleShot(True)
            self.sleep_timer.start(minutes * 60 * 1000)
            self.sleep_timer_end_time = datetime.now() + timedelta(minutes=minutes)
            self.tray.showMessage(self.translator.tr("sleep_timer"), 
                                  self.translator.tr("sleep_timer_set", min=minutes),
                                  QSystemTrayIcon.MessageIcon.Information, 3000)
        self.build_tray_menu()

    def set_custom_sleep_timer(self):
        """Opens a dialog to set a custom sleep timer duration."""
        minutes, ok = QInputDialog.getInt(self, self.translator.tr("sleep_timer"), 
                                          self.translator.tr("enter_minutes"), 
                                          value=30, minValue=1, maxValue=1440)
        if ok:
            self.set_sleep_timer(minutes)

    def on_sleep_timer_triggered(self):
        """Stops playback when the sleep timer expires."""
        mpc.stop()
        mpc.clear()
        # Ustaw blokadę ręczną, aby demon nie wznowił odtwarzania z harmonogramu
        MANUAL_OVERRIDE_LOCK.touch()
        self.manual_override_status = True
        self.sleep_timer_end_time = None
        
        self.tray.showMessage(self.translator.tr("sleep_timer"), 
                              self.translator.tr("sleep_timer_triggered"),
                              QSystemTrayIcon.MessageIcon.Information, 5000)
        self.update_return_to_schedule_button()
        self.update_tray_icon()
        self.build_tray_menu()

    def on_timer_tick(self):
        """Periodic timer handler to refresh dynamic UI elements."""
        # Sprawdź czy nastąpił auto-resume (zewnętrzne usunięcie pliku blokady)
        current_override_status = MANUAL_OVERRIDE_LOCK.exists()
        if self.manual_override_status and not current_override_status:
            logger.info("Auto-resume detected: Manual override lock removed externally.")
            self.tray.showMessage(
                self.translator.tr("auto_resume_notification_title"),
                self.translator.tr("auto_resume_notification_text"),
                QSystemTrayIcon.MessageIcon.Information,
                5000
            )
            # Wymuś odświeżenie elementów UI zależnych od blokady
            self.update_return_to_schedule_button()
            self.update_tray_icon()
            self.build_tray_menu()
        
        self.manual_override_status = current_override_status

        # Jeśli sleep timer jest aktywny, odśwież menu tray, aby zaktualizować licznik minut
        if self.sleep_timer_end_time:
            self.build_tray_menu()

        current_song_url = mpc.get_current_url() # type: ignore
        # Odświeżaj tylko, jeśli coś się zmieniło
        if current_song_url != self.last_known_song:
            self.last_known_song = current_song_url
            self.update_playing_station_in_tree() # Użyj nowej, wydajnej metody
            self.update_tray_icon()

        # Zawsze odświeżaj dynamiczne elementy, które mogły się zmienić (głośność, status)
        self.update_tray_tooltip()
        self.update_dynamic_tray_elements()

        # Odświeżaj zakładkę "About" i metadane utworu tylko, gdy okno jest widoczne
        if self.isVisible():
            self.initial_ui_refresh() # Użyj tej samej funkcji do odświeżania widocznych elementów

    def initial_ui_refresh(self):
        """Refreshes UI elements that depend on external state (like MPD). Called once at start and then by timer."""
        self.about_tab.update_content()
        self.update_volume_slider_status()
        
        current_display = mpc.get_current()
        current_url = mpc.get_current_url()

        # Jeśli MPD zwraca URL jako tytuł (brak metadanych) lub nic nie zwraca, spróbuj wyświetlić nazwę stacji
        if current_display == "–" or (current_url and current_display == current_url) or (current_display and "://" in current_display):
             if current_url:
                 # Znajdź stację po URL
                 station = next((s for s in self.stations if s["url"] == current_url), None)
                 if station:
                     current_display = station["name"]

        self.now_playing_label.setText(self.translator.tr("now_playing", current=current_display))
        self.update_player_metadata()
        


    def play_next_station(self):
        """Plays the next station in the list."""
        if not self.stations: return
        current_url = self.last_known_song
        idx = -1
        for i, s in enumerate(self.stations):
            if s["url"] == current_url:
                idx = i
                break
        
        next_idx = (idx + 1) % len(self.stations)
        play_now(self.stations[next_idx])
        self.now_playing_label.setText(self.translator.tr("now_playing", current=self.stations[next_idx]["name"]))
        self.last_known_song = self.stations[next_idx]["url"]
        self.update_playing_station_in_tree()
        self.update_return_to_schedule_button()
        self.update_tray_icon()
        self.initial_ui_refresh()

    def play_prev_station(self):
        """Plays the previous station in the list."""
        if not self.stations: return
        current_url = self.last_known_song
        idx = -1
        for i, s in enumerate(self.stations):
            if s["url"] == current_url:
                idx = i
                break
        
        prev_idx = (idx - 1 + len(self.stations)) % len(self.stations)
        play_now(self.stations[prev_idx])
        self.now_playing_label.setText(self.translator.tr("now_playing", current=self.stations[prev_idx]["name"]))
        self.last_known_song = self.stations[prev_idx]["url"]
        self.update_playing_station_in_tree()
        self.update_return_to_schedule_button()
        self.update_tray_icon()
        self.initial_ui_refresh()

    def toggle_mute(self):
        """Toggles mute state."""
        vol = mpc.get_volume()
        if vol is not None and vol > 0:
            self.previous_volume = vol
            mpc.set_volume(0)
        else:
            target = self.previous_volume if self.previous_volume > 0 else 50
            mpc.set_volume(target)

    def show(self):
        super().show()
        self.activateWindow()

    def validate_config(self, config):
        """Validates the structure of the loaded configuration."""
        if not isinstance(config, dict):
            return False, "Root must be a dictionary."
        
        if "stations" in config:
            if not isinstance(config["stations"], list):
                return False, "'stations' must be a list."
            for i, s in enumerate(config["stations"]):
                if not isinstance(s, dict):
                    return False, f"Station at index {i} must be a dictionary."
                if "name" not in s or "url" not in s:
                    return False, f"Station at index {i} missing 'name' or 'url'."

        if "schedule" in config:
            if not isinstance(config["schedule"], dict):
                return False, "'schedule' must be a dictionary."
            if "weekly" in config["schedule"] and not isinstance(config["schedule"]["weekly"], list):
                 return False, "'schedule.weekly' must be a list."

        return True, ""

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
                    "block_manual": True, # Default: manual overrides news
                    "start_minute_offset": 55,
                    "use_advanced": False,
                    "simple": {"station": "TOK FM – News", "days": ["mon","tue","wed","thu","fri"],
                               "from": "06:00", "to": "20:00", "interval_minutes": 30, "duration_minutes": 8},
                    "advanced": []
                },
            },
            "language": "pl", # Default language
            "shortcuts": default_shortcuts, # Default shortcuts
            "hide_on_startup": False,
            "auto_resume_minutes": 0 # Default: disabled

        }
        if not CONFIG_PATH.exists():
            return default
        try:
            # Load existing config
            with open(CONFIG_PATH, "r", encoding="utf-8") as f:
                user_config = yaml.safe_load(f) or {}

            # Validate loaded config
            is_valid, error_msg = self.validate_config(user_config)
            if not is_valid:
                backup_path = CONFIG_PATH.with_suffix(".yaml.bak")
                shutil.copy(CONFIG_PATH, backup_path)
                logger.error(f"Invalid config structure: {error_msg}. Backed up to {backup_path}")
                QMessageBox.warning(None, "Config Error", 
                                    f"Configuration file is invalid: {error_msg}\n\nBacked up to: {backup_path}\n\nLoading default settings.")
                user_config = {} # Force defaults

            # Deep merge user config into defaults
            default.update(user_config)
            if 'schedule' in user_config:
                default['schedule'].update(user_config['schedule'])
            if 'shortcuts' in user_config:
                default['shortcuts'].update(user_config['shortcuts'])

        except Exception as e:
            logger.critical(f"Błąd odczytu pliku konfiguracyjnego: {e}", exc_info=True)
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
        self.play_action.setText(self.translator.tr("play"))
        self.stop_action.setText(self.translator.tr("stop"))
        self.delete_station_action.setText(self.translator.tr("delete_station"))
        self.play_station_action.setText(self.translator.tr("play_station"))
        self.add_to_favorites_action.setText(self.translator.tr("add_to_favorites"))
        self.remove_from_favorites_action.setText(self.translator.tr("remove_from_favorites"))
        self.set_as_default_action.setText(self.translator.tr("set_as_default"))
        self.restart_daemon_action.setText(self.translator.tr("restart_daemon"))
        self.no_news_today_action.setText(self.translator.tr("disable_news_today"))

        self.tabs.setTabText(0, self.translator.tr("player_tab_title"))
        self.tabs.setTabText(1, self.translator.tr("stations_tab_title"))
        self.tabs.setTabText(2, self.translator.tr("schedule_tab_title"))
        self.tabs.setTabText(3, self.translator.tr("news_tab_title"))
        self.tabs.setTabText(4, self.translator.tr("settings_tab_title"))
        self.tabs.setTabText(5, self.translator.tr("mpd_config_tab_title"))
        self.tabs.setTabText(6, self.translator.tr("about_tab_title"))
        # Explicitly call retranslate on the child widget
        self.about_tab.update_content()

    def restart_scheduler_daemon(self):
        """Restarts the background scheduler daemon process."""
        subprocess.run(["pkill", "-f", "radio-scheduler.py"], check=False)
        subprocess.Popen([sys.executable, str(DAEMON_PATH)], start_new_session=True)
        QMessageBox.information(self, self.translator.tr("restart_daemon"), self.translator.tr("daemon_restarted"))

    def update_player_metadata(self):
        """Updates bitrate and format labels using raw MPD status."""
        status = mpc.get_status_dict()
        
        # Bitrate
        bitrate = status.get('bitrate', '0')
        if bitrate and bitrate != '0':
            self.bitrate_label.setText(f"{bitrate} {self.translator.tr('kbps')}")
        else:
            self.bitrate_label.setText("")

        # Audio Format (rate:bits:channels) e.g., 44100:24:2
        audio = status.get('audio')
        if audio and ':' in audio:
            try:
                rate, bits, chans = audio.split(':')
                rate_khz = float(rate) / 1000
                ch_str = self.translator.tr("stereo") if chans == '2' else (self.translator.tr("mono") if chans == '1' else f"{chans} ch")
                bits_str = f"{bits} {self.translator.tr('bits')}" if bits != 'f' else "float"
                self.format_label.setText(f"{rate_khz:g} {self.translator.tr('khz')} | {bits_str} | {ch_str}")
            except ValueError:
                self.format_label.setText(audio)
        else:
            self.format_label.setText("")

    # === ODTWARZACZ ===
    def tab_player(self):
        """Creates the 'Player' tab widget."""
        w = QWidget()
        main_layout = QVBoxLayout(w)
        main_layout.setAlignment(Qt.AlignCenter)

        # Etykieta na aktualnie grany utwór
        self.now_playing_label = QLabel(self.translator.tr("now_playing", current="..."))
        self.now_playing_label.setFont(QFont("Arial", 16))
        self.now_playing_label.setWordWrap(True)
        self.now_playing_label.setAlignment(Qt.AlignCenter)
        main_layout.addWidget(self.now_playing_label)

        # --- Dashboard / Clock Stack ---
        self.player_dashboard_stack = QStackedWidget()
        
        self.digital_clock = DigitalClock(self)
        self.analog_clock = AnalogClock(self)
        
        self.player_dashboard_stack.addWidget(self.digital_clock)
        self.player_dashboard_stack.addWidget(self.analog_clock)
        
        # Set initial widget based on config
        clock_type = self.config.get("player_clock_type", "digital")
        if clock_type == "analog":
            self.player_dashboard_stack.setCurrentWidget(self.analog_clock)
        else:
            self.player_dashboard_stack.setCurrentWidget(self.digital_clock)

        main_layout.addWidget(self.player_dashboard_stack)
        self.schedule_info = ScheduleInfoWidget(self)
        main_layout.addWidget(self.schedule_info)
        main_layout.addSpacing(10)

        # Przyciski Play/Stop
        player_controls_layout = QHBoxLayout()
        
        prev_btn = QPushButton(self.translator.tr("prev_station"))
        prev_btn.setIcon(self.style().standardIcon(QStyle.StandardPixmap.SP_MediaSkipBackward))
        prev_btn.clicked.connect(self.play_prev_station)

        play_btn = QPushButton(self.translator.tr("play"))
        play_btn.setIcon(get_icon("play", QStyle.StandardPixmap.SP_MediaPlay))
        play_btn.clicked.connect(self.play_action.trigger)
        
        stop_btn = QPushButton(self.translator.tr("stop"))
        stop_btn.setIcon(get_icon("stop", QStyle.StandardPixmap.SP_MediaStop))
        stop_btn.clicked.connect(self.stop_action.trigger)

        next_btn = QPushButton(self.translator.tr("next_station"))
        next_btn.setIcon(self.style().standardIcon(QStyle.StandardPixmap.SP_MediaSkipForward))
        next_btn.clicked.connect(self.play_next_station)

        player_controls_layout.addStretch()
        player_controls_layout.addWidget(prev_btn)
        player_controls_layout.addWidget(play_btn)
        player_controls_layout.addWidget(stop_btn)
        player_controls_layout.addWidget(next_btn)
        player_controls_layout.addStretch()
        main_layout.addLayout(player_controls_layout)

        # Kontrolki głośności
        vol_layout = QHBoxLayout()
        
        # Przycisk Mute zamiast etykiety tekstowej
        self.mute_btn = QPushButton()
        self.mute_btn.setIcon(get_icon("volume", QStyle.StandardPixmap.SP_MediaVolume))
        self.mute_btn.setFlat(True) # Wygląda jak ikona
        self.mute_btn.clicked.connect(self.toggle_mute)
        self.mute_btn.setToolTip(self.translator.tr("mute"))

        self.volume_slider = QSlider(Qt.Horizontal)
        self.volume_slider.setRange(0, 100)
        self.volume_slider.valueChanged.connect(mpc.set_volume)
        
        # Pasek postępu (wizualizacja)
        self.volume_progress = QProgressBar()
        self.volume_progress.setRange(0, 100)
        self.volume_progress.setTextVisible(False)
        self.volume_progress.setFixedWidth(100)
        self.volume_progress.setStyleSheet("""
            QProgressBar {
                border: 1px solid #bbb;
                border-radius: 4px;
                background: #eee;
                height: 10px;
            }
            QProgressBar::chunk {
                background-color: qlineargradient(spread:pad, x1:0, y1:0, x2:1, y2:0, 
                                                  stop:0 #4CAF50, stop:0.6 #FFEB3B, stop:1 #F44336);
                border-radius: 4px;
            }
        """)
        self.volume_slider.valueChanged.connect(self.volume_progress.setValue)

        vol_layout.addWidget(self.mute_btn)
        vol_layout.addWidget(self.volume_slider)
        vol_layout.addWidget(self.volume_progress)
        main_layout.addLayout(vol_layout)

        # Sekcja metadanych (Bitrate / Format)
        meta_layout = QHBoxLayout()
        self.bitrate_label = QLabel("")
        self.format_label = QLabel("")
        
        meta_font = QFont("Arial", 9)
        self.bitrate_label.setFont(meta_font); self.bitrate_label.setStyleSheet("color: #666;")
        self.format_label.setFont(meta_font); self.format_label.setStyleSheet("color: #666;")

        meta_layout.addStretch()
        meta_layout.addWidget(self.bitrate_label)
        meta_layout.addSpacing(20)
        meta_layout.addWidget(self.format_label)
        meta_layout.addStretch()
        
        main_layout.addSpacing(10)
        main_layout.addLayout(meta_layout)

        return w

    # === STACJE ===
    def tab_stations(self):
        """Creates the 'Stations' tab widget."""
        w = QWidget()
        main_layout = QHBoxLayout(w)

        # Lewa strona z filtrem i drzewem
        left_vbox = QVBoxLayout()

        self.station_filter_input = QLineEdit()
        self.station_filter_input.setPlaceholderText(self.translator.tr("filter_placeholder"))
        self.station_filter_input.textChanged.connect(self.filter_stations_tree)
        left_vbox.addWidget(self.station_filter_input)

        self.tree = QTreeWidget()
        self.tree.setHeaderLabels([self.translator.tr("stations_tab_title")])
        self.tree.header().setVisible(False)
        self.tree.itemDoubleClicked.connect(self.play_from_tree)
        # Ustawienie polityki menu kontekstowego
        self.tree.setContextMenuPolicy(Qt.CustomContextMenu)
        self.tree.customContextMenuRequested.connect(self.show_station_context_menu)
        self.refresh_tree()
        left_vbox.addWidget(self.tree)
        main_layout.addLayout(left_vbox, 3)

        btns = QVBoxLayout()
        add = QPushButton(self.translator.tr("add")); add.clicked.connect(self.add_station_action.trigger)
        add.setStyleSheet("background-color: #4CAF50; color: white;")
        edit = QPushButton(self.translator.tr("edit")); edit.clicked.connect(self.edit_station_action.trigger)
        edit.setStyleSheet("background-color: #2196F3; color: white;")
        delete = QPushButton(self.translator.tr("delete")); delete.clicked.connect(self.delete_station_action.trigger)
        delete.setStyleSheet("background-color: #f44336; color: white;")

        # Przyciski do zmiany kolejności
        reorder_layout = QHBoxLayout()
        move_up_btn = QPushButton(self.translator.tr("move_up")); move_up_btn.clicked.connect(self.move_station_up)
        move_down_btn = QPushButton(self.translator.tr("move_down")); move_down_btn.clicked.connect(self.move_station_down)
        reorder_layout.addWidget(move_up_btn)
        reorder_layout.addWidget(move_down_btn)
        
        self.tree.setFocus() # Ustaw fokus na drzewie, aby skróty od razu działały

        # Przycisk Zastosuj dla stacji
        self.apply_stations_btn = QPushButton(self.translator.tr("apply_stations"))
        self.apply_stations_btn.clicked.connect(self.save_stations_only)
        self.apply_stations_btn.setEnabled(False) # Domyślnie wyłączony
        self.apply_stations_btn.setStyleSheet("background-color: #008CBA; color: white;")

        btns.addWidget(add); btns.addWidget(edit); btns.addWidget(delete)
        
        import_btn = QPushButton(self.translator.tr("import_playlist"))
        import_btn.clicked.connect(self.import_stations_from_playlist)
        btns.addWidget(import_btn)

        btns.addSpacing(20)
        btns.addLayout(reorder_layout)
        btns.addStretch()
        btns.addWidget(self.apply_stations_btn)

        # Przycisk powrotu do harmonogramu
        self.return_to_schedule_btn = QPushButton(self.translator.tr("return_to_schedule"))
        self.return_to_schedule_btn.clicked.connect(self.return_to_schedule)
        self.return_to_schedule_btn.setStyleSheet("background-color: #f44336; color: white;")
        btns.addWidget(self.return_to_schedule_btn)
        self.update_return_to_schedule_button()

        main_layout.addLayout(btns, 1)
        return w

    def filter_stations_tree(self):
        """Filters the station tree based on the text in the filter input."""
        filter_text = self.station_filter_input.text().lower()
        root = self.tree.invisibleRootItem()
        for i in range(root.childCount()):
            genre_item = root.child(i)
            # Check if the genre name itself matches
            genre_matches = filter_text in genre_item.text(0).lower()
            any_child_matches = False

            # Iterate through stations within the genre
            for j in range(genre_item.childCount()):
                station_item = genre_item.child(j)
                station_matches = filter_text in station_item.text(0).lower()
                # Stacja powinna być widoczna, jeśli jej nazwa pasuje LUB nazwa jej gatunku pasuje
                station_item.setHidden(not (station_matches or genre_matches))
                if station_matches:
                    any_child_matches = True
            
            # Gatunek powinien być widoczny, jeśli jego nazwa pasuje LUB którakolwiek z jego stacji pasuje
            genre_item.setHidden(not (genre_matches or any_child_matches))

    def update_volume_slider_status(self):
        """Disables the volume slider and updates its label if MPD is not running."""
        volume = mpc.get_volume()
        if volume is not None:
            self.volume_slider.setEnabled(True)
            self.mute_btn.setEnabled(True)
            if not self.volume_slider.isSliderDown():
                self.volume_slider.setValue(volume)
                self.volume_progress.setValue(volume)
            
            # Update mute icon based on volume
            if volume == 0:
                self.mute_btn.setIcon(self.style().standardIcon(QStyle.StandardPixmap.SP_MediaVolumeMuted))
                self.mute_btn.setToolTip(self.translator.tr("unmute"))
            else:
                self.mute_btn.setIcon(get_icon("volume", QStyle.StandardPixmap.SP_MediaVolume))
                self.mute_btn.setToolTip(self.translator.tr("mute"))
        else:
            self.volume_slider.setEnabled(False)
            self.mute_btn.setEnabled(False)
            self.volume_progress.setValue(0)

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

                icon = get_icon("play", QStyle.StandardPixmap.SP_MediaPlay) if is_playing else QIcon()
                item.setIcon(0, icon)

            iterator += 1

    def refresh_tree(self, mark_dirty=False):
        """Refreshes the station tree view, optionally marking the state as dirty (needs saving)."""
        self.tree.clear()
        current_url = self.last_known_song
        default_station_name = self.schedule.get("default")

        groups = defaultdict(list)
        for s in self.stations: # Use self.stations directly
            g = s.get("genre") or self.translator.tr("genre_none")
            groups[g].append(s)

        for genre, stations in sorted(groups.items()):
            parent = QTreeWidgetItem(self.tree, [genre])
            parent.setFlags(parent.flags() & ~Qt.ItemIsSelectable)
            for s in stations:
                is_playing = s['url'] == current_url
                is_favorite = s.get("favorite", False)
                is_default = s['name'] == default_station_name

                display_name = s['name']
                if is_favorite:
                    display_name = f"★ {display_name}"
                if is_default:
                    display_name = f"{display_name} ({self.translator.tr('default_station_indicator')})"

                item = QTreeWidgetItem(parent, [display_name])
                item.setData(0, Qt.UserRole, s)
                font = item.font(0)
                font.setBold(is_playing)
                font.setItalic(is_default)
                item.setFont(0, font)
                if is_playing:
                    item.setIcon(0, get_icon("play", QStyle.StandardPixmap.SP_MediaPlay))
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
        self.refresh_tree(mark_dirty=True)
        self.refresh_default_station_combo()

    def play_from_tree(self):
        """Plays the currently selected station from the tree."""
        item = self.tree.currentItem()
        if not item or item.parent() is None: return
        station = item.data(0, Qt.UserRole)
        if station:
            play_now(station)
            self.now_playing_label.setText(self.translator.tr("now_playing", current=station["name"]))
            # Natychmiast zaktualizuj bufor, aby interfejs odświeżył się od razu
            self.last_known_song = station.get("url")
            self.update_return_to_schedule_button()
            self.update_playing_station_in_tree() # Użyj wydajnej metody
            self.update_tray_icon()

    def return_to_schedule(self):
        """Removes the manual override lock, allowing the scheduler to take control again."""
        MANUAL_OVERRIDE_LOCK.unlink(missing_ok=True)
        self.manual_override_status = False # Zapobiegamy powiadomieniu, bo to akcja użytkownika
        self.update_return_to_schedule_button()
        self.build_tray_menu() # Odśwież menu w trayu
        self.update_tray_icon()

    def toggle_no_news_today(self, checked):
        """Creates or removes the lock file to disable news for the current day."""
        if checked:
            today_str = str(datetime.now().date())
            NO_NEWS_TODAY_LOCK.write_text(today_str, encoding="utf-8")
        else:
            NO_NEWS_TODAY_LOCK.unlink(missing_ok=True)

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
        
        l.addRow(self.translator.tr("name"), name)
        l.addRow(self.translator.tr("url"), url)
        
        # Test Connection Button
        test_layout = QHBoxLayout()
        test_btn = QPushButton(self.translator.tr("test_connection"))
        test_status_label = QLabel("")
        test_btn.clicked.connect(lambda: self.test_station_connection(url.text(), test_btn, test_status_label))
        test_layout.addWidget(test_btn); test_layout.addWidget(test_status_label); test_layout.addStretch()
        l.addRow("", test_layout)

        l.addRow(self.translator.tr("genre"), genre); l.addRow("", fav)
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

    def test_station_connection(self, url_str, btn, label):
        """Tests the connectivity of the given URL using a HEAD request."""
        url_str = url_str.strip()
        if not url_str: return
        
        btn.setEnabled(False)
        label.setText(self.translator.tr("testing"))
        label.setStyleSheet("color: black;")
        
        req = QNetworkRequest(QUrl(url_str))
        req.setRawHeader(b"User-Agent", b"RadioScheduler/1.0")
        
        # Store reply to prevent garbage collection
        self._current_test_reply = self.nam.head(req)
        self._current_test_reply.finished.connect(lambda: self.on_test_finished(self._current_test_reply, btn, label))

    def on_test_finished(self, reply, btn, label):
        """Callback for the connection test."""
        btn.setEnabled(True)
        err = reply.error()
        code = reply.attribute(QNetworkRequest.Attribute.HttpStatusCodeAttribute)
        
        if err == QNetworkReply.NetworkError.NoError and 200 <= code < 400:
            label.setText(self.translator.tr("connection_ok", code=code))
            label.setStyleSheet("color: green;")
        else:
            error_msg = f"HTTP {code}" if code else reply.errorString()
            label.setText(self.translator.tr("connection_failed", error=error_msg))
            label.setStyleSheet("color: red;")
        
        reply.deleteLater()
        self._current_test_reply = None

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

    def import_stations_from_playlist(self):
        """Imports radio stations from M3U or PLS playlist files."""
        file_path, _ = QFileDialog.getOpenFileName(self, self.translator.tr("import_playlist_dialog_title"),
                                                   str(Path.home()),
                                                   f"{self.translator.tr('playlist_files')} (*.m3u *.m3u8 *.pls)")
        if not file_path:
            return

        try:
            path = Path(file_path)
            content = path.read_text(encoding='utf-8', errors='ignore')
            new_stations = []

            if path.suffix.lower() in ['.m3u', '.m3u8']:
                lines = content.splitlines()
                current_title = None
                for line in lines:
                    line = line.strip()
                    if not line: continue
                    if line.startswith("#EXTINF:"):
                        # Format: #EXTINF:-1,Title
                        parts = line.split(',', 1)
                        if len(parts) > 1:
                            current_title = parts[1].strip()
                    elif not line.startswith("#"):
                        url = line
                        name = current_title if current_title else path.stem
                        new_stations.append({"name": name, "url": url, "genre": None, "favorite": False})
                        current_title = None
            
            elif path.suffix.lower() == '.pls':
                parser = configparser.ConfigParser()
                try:
                    parser.read_string(content)
                except configparser.MissingSectionHeaderError:
                    parser.read_string(f"[playlist]\n{content}")
                
                # Szukaj sekcji playlist (case-insensitive)
                section = next((parser[sec] for sec in parser.sections() if sec.lower() == 'playlist'), None)
                if section:
                    count = int(section.get('numberofentries', 0))
                    for i in range(1, count + 1):
                        url = section.get(f"file{i}")
                        title = section.get(f"title{i}", f"Station {i}")
                        if url:
                            new_stations.append({"name": title, "url": url, "genre": None, "favorite": False})

            if new_stations:
                self.stations.extend(new_stations)
                self.config["stations"] = self.stations
                self.refresh_tree(mark_dirty=True)
                QMessageBox.information(self, self.translator.tr("success"), 
                                        self.translator.tr("imported_count", count=len(new_stations)))
            else:
                QMessageBox.warning(self, self.translator.tr("error"), self.translator.tr("import_error"))

        except Exception as e:
            logger.error(f"Error importing playlist: {e}")
            QMessageBox.critical(self, self.translator.tr("error"), f"{self.translator.tr('import_error')}:\n{e}")

    # === HARMONOGRAM + NEWS + ABOUT ===
    def tab_schedule(self):
        """Creates the 'Schedule' tab widget."""
        w = QWidget()
        l = QHBoxLayout(w)

        # Lewa strona - tabela reguł
        left_vbox = QVBoxLayout() # Left side for schedule rules
        left_vbox.addWidget(QLabel(self.translator.tr("schedule_rules")))
        self.schedule_table = QTableWidget()
        self.schedule_table.setColumnCount(3)
        self.schedule_table.setHorizontalHeaderLabels([
            self.translator.tr("days"),
            self.translator.tr("time_range"),
            self.translator.tr("station")
        ])
        self.schedule_table.setSelectionBehavior(QAbstractItemView.SelectRows)
        self.schedule_table.setEditTriggers(QAbstractItemView.NoEditTriggers)
        self.schedule_table.verticalHeader().setVisible(False)
        self.schedule_table.horizontalHeader().setStretchLastSection(True)
        self.schedule_table.setAlternatingRowColors(True)
        self.refresh_schedule_list()
        left_vbox.addWidget(self.schedule_table)

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
        self.schedule_table.setRowCount(0)
        day_map = {
            "mon": self.translator.tr("day_mon_short"), "tue": self.translator.tr("day_tue_short"),
            "wed": self.translator.tr("day_wed_short"), "thu": self.translator.tr("day_thu_short"),
            "fri": self.translator.tr("day_fri_short"), "sat": self.translator.tr("day_sat_short"), "sun": self.translator.tr("day_sun_short")
        }
        for i, rule in enumerate(self.schedule.get("weekly", [])):
            row_position = self.schedule_table.rowCount()
            self.schedule_table.insertRow(row_position)

            days = ", ".join([day_map.get(d, d) for d in rule["days"]])
            days_item = QTableWidgetItem(days)
            days_item.setData(Qt.UserRole, i) # Store index in the first column's item

            self.schedule_table.setItem(row_position, 0, days_item)
            self.schedule_table.setItem(row_position, 1, QTableWidgetItem(f"{rule['from']}–{rule['to']}"))
            self.schedule_table.setItem(row_position, 2, QTableWidgetItem(rule['station']))

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
        current_row = self.schedule_table.currentRow()
        if current_row < 0: return
        item = self.schedule_table.item(current_row, 0)
        idx = item.data(Qt.UserRole) if item else -1
        rule = self.schedule["weekly"][idx]
        dlg = TimeRangeEditor(rule, self.tree, self)
        new_rule = dlg.get_rule()
        if new_rule:
            self.schedule["weekly"][idx] = new_rule
            # Zmiana na zapis po kliknięciu przycisku
            self.refresh_schedule_list()

    def delete_schedule_rule(self):
        """Deletes the selected schedule rule after confirmation."""
        current_row = self.schedule_table.currentRow()
        if current_row < 0: return
        item = self.schedule_table.item(current_row, 0)
        idx = item.data(Qt.UserRole) if item else -1
        if QMessageBox.question(self, self.translator.tr("delete_prompt"), self.translator.tr("delete_rule_prompt")) == QMessageBox.Yes:
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
            logger.error(f"Błąd zapisu pliku konfiguracyjnego (tylko stacje): {e}")
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
            logger.error(f"Błąd zapisu pliku konfiguracyjnego: {e}")
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
        
        self.news_block_manual = QCheckBox(self.translator.tr("block_news_manual"))
        self.news_block_manual.setChecked(self.news_config.get("block_manual", True))

        offset_layout = QHBoxLayout()
        offset_layout.addWidget(QLabel(self.translator.tr("news_offset_label")))
        self.news_offset = QSpinBox(minimum=0, maximum=59, value=self.news_config.get("start_minute_offset", 0))
        offset_layout.addWidget(self.news_offset)
        offset_layout.addStretch()

        main_layout.addWidget(self.news_enabled)
        main_layout.addWidget(self.news_block_manual)
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
        self.news_config["block_manual"] = self.news_block_manual.isChecked()
        self.news_config["use_advanced"] = self.advanced_mode_radio.isChecked()
        self.news_config["start_minute_offset"] = self.news_offset.value()
        
        # Preserve existing days or default to all days to prevent config corruption
        current_simple = self.news_config.get("simple", {})
        days = current_simple.get("days", ["mon", "tue", "wed", "thu", "fri", "sat", "sun"])
        
        self.news_config["simple"] = {
            "station": self.news_station.currentText(),
            "from": self.news_from.time().toString("HH:mm"),
            "to": self.news_to.time().toString("HH:mm"),
            "interval_minutes": self.news_interval.value(),
            "duration_minutes": self.news_duration.value(),
            "days": days
        }
        # Zaawansowane reguły są już w self.news_config["advanced"]

    # === MPD CONFIG EDITOR ===
    def tab_mpd_config(self):
        """Creates the 'MPD Config' tab widget with a text editor."""
        w = QWidget()
        self.mpd_config_layout = QVBoxLayout(w)

        self.mpd_conf_path = find_mpd_conf_path()

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
            logger.error(f"Błąd odczytu pliku mpd.conf: {e}")

    def save_mpd_config(self):
        """Saves the content of the text editor to the mpd.conf file."""
        try:
            content = self.mpd_conf_editor.toPlainText()
            self.mpd_conf_path.parent.mkdir(parents=True, exist_ok=True)
            self.mpd_conf_path.write_text(content, encoding="utf-8")
            QMessageBox.information(self, self.translator.tr("saved"), self.translator.tr("mpd_conf_save_success", path=self.mpd_conf_path))
        except Exception as e:
            QMessageBox.critical(self, self.translator.tr("save_error"), self.translator.tr("mpd_conf_save_error", e=e))
            logger.error(f"Błąd zapisu pliku mpd.conf: {e}")

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
            logger.error(f"Błąd krytyczny podczas restartu MPD: {e}")

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

        backup_btn = QPushButton(self.translator.tr("create_backup_zip"))
        backup_btn.clicked.connect(self.create_backup_zip)

        imex_layout.addWidget(backup_btn)
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
        
        # --- Other settings ---
        other_group = QGroupBox(self.translator.tr("other_settings_title"))
        other_layout = QVBoxLayout(other_group)
        
        self.hide_on_startup_checkbox = QCheckBox(self.translator.tr("hide_on_startup_checkbox"))
        self.hide_on_startup_checkbox.setChecked(self.config.get("hide_on_startup", False))
        other_layout.addWidget(self.hide_on_startup_checkbox)

        auto_resume_layout = QHBoxLayout()
        auto_resume_layout.addWidget(QLabel(self.translator.tr("auto_resume_label")))
        self.auto_resume_spin = QSpinBox()
        self.auto_resume_spin.setRange(0, 1440) # Max 24h
        self.auto_resume_spin.setValue(self.config.get("auto_resume_minutes", 0))
        self.auto_resume_spin.setSuffix(" min")
        auto_resume_layout.addWidget(self.auto_resume_spin)
        auto_resume_layout.addWidget(QLabel(f"({self.translator.tr('auto_resume_hint')})"))
        other_layout.addLayout(auto_resume_layout)

        # Clock type setting
        clock_type_layout = QHBoxLayout()
        clock_type_layout.addWidget(QLabel(self.translator.tr("player_clock_type")))
        self.clock_type_combo = QComboBox()
        self.clock_type_combo.addItem(self.translator.tr("clock_digital"), "digital")
        self.clock_type_combo.addItem(self.translator.tr("clock_analog"), "analog")
        current_clock_type = self.config.get("player_clock_type", "digital")
        idx = self.clock_type_combo.findData(current_clock_type)
        if idx != -1: self.clock_type_combo.setCurrentIndex(idx)
        clock_type_layout.addWidget(self.clock_type_combo)
        other_layout.addLayout(clock_type_layout)

        save_other_btn = QPushButton(self.translator.tr("save_other_settings"))
        save_other_btn.clicked.connect(self.save_simple_settings)
        other_layout.addWidget(save_other_btn)

        layout.addWidget(other_group)


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
                logger.error(f"Error creating autostart file: {e}")
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

    def create_backup_zip(self):
        """Creates a full backup (config + logs) in a ZIP archive."""
        file_path, _ = QFileDialog.getSaveFileName(self, self.translator.tr("backup_zip_title"),
                                                   str(Path.home() / "radio-scheduler-full-backup.zip"),
                                                   "ZIP Files (*.zip)")
        if file_path:
            try:
                with zipfile.ZipFile(file_path, 'w', zipfile.ZIP_DEFLATED) as zipf:
                    if CONFIG_PATH.exists():
                        zipf.write(CONFIG_PATH, arcname="config.yaml")
                    if LOG_PATH.exists():
                        zipf.write(LOG_PATH, arcname="radio-scheduler-gui.log")
                    daemon_log = Path.home() / ".config/radio-scheduler/radio-scheduler.log"
                    if daemon_log.exists():
                        zipf.write(daemon_log, arcname="radio-scheduler.log")
                QMessageBox.information(self, self.translator.tr("success"),
                                        self.translator.tr("backup_success", path=file_path))
            except Exception as e:
                QMessageBox.critical(self, self.translator.tr("error"),
                                     self.translator.tr("backup_error", e=e))

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

    def save_simple_settings(self):
        """Saves simple boolean settings directly to the config file."""
        self.config["hide_on_startup"] = self.hide_on_startup_checkbox.isChecked()
        self.config["auto_resume_minutes"] = self.auto_resume_spin.value()
        self.config["player_clock_type"] = self.clock_type_combo.currentData()
        try:
            with open(CONFIG_PATH, "w", encoding="utf-8") as f:
                yaml.safe_dump(self.config, f, allow_unicode=True, sort_keys=False)
            self.statusBar().showMessage(self.translator.tr("settings_saved"), 2000)
            self.update_player_clock_view() # Update view after saving
        except Exception as e:
            logger.error(f"Błąd zapisu prostych ustawień: {e}")
            QMessageBox.critical(self, self.translator.tr("save_error"), self.translator.tr("config_save_error", e=e))

    def update_player_clock_view(self):
        """Switches between digital and analog clock in the player tab."""
        clock_type = self.config.get("player_clock_type", "digital")
        if clock_type == "analog":
            self.player_dashboard_stack.setCurrentWidget(self.analog_clock)
        else:
            self.player_dashboard_stack.setCurrentWidget(self.digital_clock)

app = QApplication(sys.argv)
app.setQuitOnLastWindowClosed(False)
if ICON_PATH.exists():
    app.setWindowIcon(QIcon(str(ICON_PATH)))

def main():
    parser = argparse.ArgumentParser(description="RadioScheduler GUI")
    parser.add_argument("--hidden", action="store_true", help="Start minimized to tray")
    parser.add_argument("--play", type=str, help="Name of the station to play on startup")
    args = parser.parse_args()

    logger.info("--- RadioScheduler GUI started ---")
    ensure_icons_exist()
    win = MainWindow()
    win.update_tray_icon()

    # Obsługa argumentu --play
    if args.play:
        station = next((s for s in win.stations if s["name"] == args.play), None)
        if station:
            logger.info(f"Auto-playing station from CLI: {args.play}")
            play_now(station)
            win.now_playing_label.setText(win.translator.tr("now_playing", current=station["name"]))
            win.last_known_song = station["url"]
            win.update_playing_station_in_tree()
            win.update_return_to_schedule_button()
            win.update_tray_icon()
        else:
            logger.warning(f"Station not found via CLI: {args.play}")

    if not args.hidden and not win.config.get("hide_on_startup", False):
        win.show()
    sys.exit(app.exec())

if __name__ == "__main__":
    try:
        main()
    except Exception as e:
        logger.critical("Aplikacja GUI napotkała nieobsługiwany błąd.", exc_info=True)
