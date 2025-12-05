#!/usr/bin/env python3
import sys
import yaml
import subprocess
from pathlib import Path
from datetime import date, datetime
import logging

from PySide6.QtWidgets import QApplication, QSystemTrayIcon, QMenu
from PySide6.QtGui import QAction, QIcon
from PySide6.QtCore import QTimer

CONFIG = Path.home() / ".config/radio-scheduler/config.yaml"
LOG_PATH = Path.home() / ".config/radio-scheduler/radio-scheduler-tray.log"
NO_NEWS = Path.home() / ".config/radio-scheduler/no-news-today"
MANUAL_OVERRIDE_LOCK = Path.home() / ".config/radio-scheduler/manual_override.lock"

logging.basicConfig(
    filename=LOG_PATH,
    level=logging.ERROR,
    format='%(asctime)s - %(levelname)s - %(message)s'
)

app = QApplication([])

tray = QSystemTrayIcon(QIcon.fromTheme("audio-headphones"))
tray.setVisible(True)

def load():
    try:
        with open(CONFIG, "r", encoding="utf-8") as f:
            return yaml.safe_load(f) or {}
    except Exception as e:
        logging.error(f"Błąd podczas ładowania pliku konfiguracyjnego: {e}")
        return {"stations": []}

def get_volume():
    try:
        return int(subprocess.getoutput("mpc volume").split()[-1].strip("%"))
    except Exception as e:
        logging.error(f"Błąd podczas odczytu głośności: {e}")
        return 50

def set_volume(v):
    try:
        v = max(0, min(100, v))
        subprocess.run(["mpc", "volume", str(v)], check=True, capture_output=True)
    except subprocess.CalledProcessError as e:
        logging.error(f"Błąd podczas ustawiania głośności: {e.stderr}")

def get_current():
    try:
        # Używamy check_output, aby przechwycić błędy, jeśli mpc nie działa
        return subprocess.check_output(["mpc", "current"], text=True).strip() or "–"
    except subprocess.CalledProcessError:
        # MPC może nie być uruchomiony lub nie grać
        return "–"
    except FileNotFoundError:
        logging.error("Polecenie 'mpc' nie zostało znalezione.")
        return "Błąd MPC"

def update_tooltip():
    current = get_current()
    vol = get_volume()
    tray.setToolTip(f"RadioScheduler\nGra: {current}\nGłośność: {vol}%")

def build():
    data = load()
    favorites = [s for s in data.get("stations", []) if s.get("favorite")]

    menu = QMenu()

    menu.addAction(f"Teraz gra: {get_current()}").setEnabled(False)
    menu.addSeparator()

    if favorites:
        for s in favorites:
            a = menu.addAction(f"★ {s['name']}")
            a.triggered.connect(lambda _, x=s: play(x))
    else:
        menu.addAction("★ Brak ulubionych").setEnabled(False)

    menu.addSeparator()

    # głośność co 5%
    vol_menu = menu.addMenu(f"Głośność: {get_volume()}%")
    for v in range(0, 101, 5):
        a = vol_menu.addAction(f"{v:3}%")
        a.triggered.connect(lambda _, vol=v: (set_volume(vol), update_tooltip(), build()))

    menu.addSeparator()

    # newsy
    news_off = NO_NEWS.exists() and NO_NEWS.read_text().strip() == str(date.today())
    news = menu.addAction("Wyłącz newsy na dziś")
    news.setCheckable(True)
    news.setChecked(news_off)
    news.triggered.connect(toggle_news)

    # Powrót do harmonogramu
    if MANUAL_OVERRIDE_LOCK.exists():
        menu.addSeparator()
        return_action = menu.addAction("Wróć do harmonogramu")
        return_action.triggered.connect(return_to_schedule)

    menu.addSeparator()
    menu.addAction("Otwórz edytor GUI").triggered.connect(lambda: subprocess.Popen([sys.executable, str(Path.home() / ".config/radio-scheduler/radio-scheduler-gui.py")]))
    menu.addAction("Wyjdź").triggered.connect(app.quit)

    tray.setContextMenu(menu)

def return_to_schedule():
    MANUAL_OVERRIDE_LOCK.unlink(missing_ok=True)
    build() # Odśwież menu, aby ukryć przycisk

def play(station):
    try:
        subprocess.run(["mpc", "clear"], check=True)
        subprocess.run(["mpc", "add", station["url"]], check=True)
        subprocess.run(["mpc", "play"], check=True)
        update_tooltip()
        tray.showMessage("RadioScheduler", station["name"], msecs=1500)
        MANUAL_OVERRIDE_LOCK.touch()
        build()
    except (subprocess.CalledProcessError, FileNotFoundError) as e:
        logging.error(f"Błąd podczas odtwarzania stacji {station.get('name', '')}: {e}")
        tray.showMessage("Błąd odtwarzania", f"Sprawdź logi: {LOG_PATH}", QIcon.fromTheme("dialog-error"), 3000)

def toggle_news():
    if NO_NEWS.exists() and NO_NEWS.read_text().strip() == str(date.today()):
        NO_NEWS.unlink(missing_ok=True)
    else:
        NO_NEWS.parent.mkdir(parents=True, exist_ok=True)
        NO_NEWS.write_text(str(date.today()))
    build()

# pierwsze uruchomienie
build()
update_tooltip()

# odświeżanie co 10 s
def refresh():
    update_tooltip()
    if tray.contextMenu():
        tray.contextMenu().actions()[0].setText(f"Teraz gra: {get_current()}")

timer = QTimer()
timer.timeout.connect(refresh)
timer.start(10000)

# PPM → odśwież
tray.activated.connect(lambda r: build() if r == QSystemTrayIcon.Context else None)

print("RadioScheduler tray – wersja ostateczna (bez scrolla, ale wszystko inne idealne)")
app.exec()
