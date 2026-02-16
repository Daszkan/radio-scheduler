#!/usr/bin/env python3
"""RadioScheduler Daemon: A background process to manage radio station playback based on a schedule."""
# Copyright (c) 2025 - 2026 Daszkan (Jacek)
#
# This software is released under the MIT License.
# https://opensource.org/licenses/MIT
import time
import yaml
import subprocess
from datetime import datetime, timedelta
from pathlib import Path
import logging
from mpc_controller import MPCController # type: ignore
from typing import Dict, Any, List, Optional

CONFIG_PATH = Path.home() / ".config/radio-scheduler/config.yaml"
LOG_PATH = Path.home() / ".config/radio-scheduler/radio-scheduler.log"
MANUAL_OVERRIDE_LOCK = Path.home() / ".config/radio-scheduler/manual_override.lock"
NO_NEWS_TODAY_LOCK = Path.home() / ".config/radio-scheduler/no-news-today"

# Konfiguracja logowania
logging.basicConfig(
    filename=LOG_PATH,
    level=logging.INFO, # Log INFO level messages as well for better diagnostics
    format='%(asctime)s - %(levelname)s - %(message)s'
)

mpc = MPCController()

def load_config() -> Dict[str, Any]:
    """Loads the YAML configuration file."""
    try:
        if not CONFIG_PATH.exists():
            return {"stations": [], "schedule": {"default": "", "weekly": [], "news_breaks": {"enabled": True}}}
        with open(CONFIG_PATH, "r", encoding="utf-8") as f:
            return yaml.safe_load(f) or {}
    except Exception as e:
        logging.error(f"Error loading configuration: {e}")
        return {"stations": [], "schedule": {}}

def find_station_url(name: str, stations: List[Dict[str, Any]]) -> Optional[str]:
    """Finds the URL for a station by its name."""
    for s in stations:
        if s["name"] == name:
            return s["url"]
    if name:
        logging.error(f"Station not found: {name}")
    return None

def main():
    was_news_playing = False
    last_logged_minute = -1
    while True:
        config = load_config()
        stations = config.get("stations", [])
        sched = config.get("schedule", {})
        now = datetime.now()
        # Fix: Use locale-independent weekday mapping (0=Monday)
        weekday_map = {0: "mon", 1: "tue", 2: "wed", 3: "thu", 4: "fri", 5: "sat", 6: "sun"}
        weekday = weekday_map[now.weekday()]
        current_time_str = now.strftime("%H:%M")        

        # Logowanie statusu co minutę dla celów debugowania
        if now.minute != last_logged_minute:
            logging.info(f"Heartbeat: Day={weekday}, Time={current_time_str}, Manual={MANUAL_OVERRIDE_LOCK.exists()}, NoNews={NO_NEWS_TODAY_LOCK.exists()}")
            last_logged_minute = now.minute

        target_station_name = None
        
        # Sprawdź flagę "bez newsów na dziś"
        no_news_today = NO_NEWS_TODAY_LOCK.exists() and NO_NEWS_TODAY_LOCK.read_text().strip() == str(now.date())
        manual_override = MANUAL_OVERRIDE_LOCK.exists()

        # Auto-resume logic
        if manual_override:
            auto_resume_minutes = config.get("auto_resume_minutes", 0)
            if auto_resume_minutes > 0:
                try:
                    # Sprawdź wiek pliku blokady
                    mtime = datetime.fromtimestamp(MANUAL_OVERRIDE_LOCK.stat().st_mtime)
                    if (now - mtime).total_seconds() / 60 > auto_resume_minutes:
                        logging.info(f"Auto-resume: Manual override expired after {auto_resume_minutes} minutes.")
                        MANUAL_OVERRIDE_LOCK.unlink(missing_ok=True)
                        manual_override = False
                except FileNotFoundError:
                    pass # Plik mógł zostać usunięty w międzyczasie

        # News breaks (advanced first)
        news_cfg = sched.get("news_breaks", {})
        news_played_this_cycle = False
        
        # Sprawdź czy newsy są włączone I (nie ma trybu ręcznego LUB tryb ręczny nie blokuje newsów)
        should_play_news = news_cfg.get("enabled", True) and (not manual_override or not news_cfg.get("block_manual", True))

        if not no_news_today and should_play_news:
            offset = news_cfg.get("start_minute_offset", 0)
            if news_cfg.get("use_advanced", False):
                for rule in news_cfg.get("advanced", []):
                    if weekday in rule["days"]:
                        start = datetime.strptime(rule["from"], "%H:%M").time()
                        end = datetime.strptime(rule["to"], "%H:%M").time()
                        if start <= now.time() <= end:
                            # Poprawiona logika: Sprawdź, czy bieżąca godzina jest w interwale i czy minuta pasuje do offsetu
                            if now.hour % (rule["interval_minutes"] / 60) == 0 if rule["interval_minutes"] >= 60 else now.minute % rule["interval_minutes"] == 0:
                                if offset <= now.minute < offset + rule.get("duration_minutes", 8):
                                    target_station_name = rule["station"]
                                    news_played_this_cycle = True
                                    break
            else: # Tryb prosty
                simple = news_cfg.get("simple", {})
                days = simple.get("days", ["mon","tue","wed","thu","fri","sat","sun"])
                if weekday in days and simple.get("station"):
                    start = datetime.strptime(simple.get("from", "00:00"), "%H:%M").time()
                    end = datetime.strptime(simple.get("to", "22:00"), "%H:%M").time()
                    if start <= now.time() <= end:
                        interval = simple.get("interval_minutes", 60)
                        duration = simple.get("duration_minutes", 8)
                        # Poprawiona logika dla trybu prostego
                        # Sprawdź, czy godzina jest wielokrotnością interwału (dla pełnych godzin)
                        # lub czy minuta jest wielokrotnością interwału (dla < 60 min)
                        is_on_interval = (now.minute == 0 and now.hour % (interval / 60) == 0) if interval >= 60 else (now.minute % interval == 0)
                        if is_on_interval and offset <= now.minute < offset + duration:
                                target_station_name = simple["station"]
                                news_played_this_cycle = True
            
            if news_played_this_cycle:
                pass # Mamy już stację z newsów

        # Weekly schedule
        if not target_station_name and not manual_override:
            rule_found = False
            for rule in sched.get("weekly", []):
                if weekday in rule["days"] and rule["from"] <= current_time_str < rule["to"]:
                    target_station_name = rule["station"]
                    rule_found = True
                    break
            if not rule_found:
                target_station_name = sched.get("default")

        # Odtwarzaj tylko jeśli jest co i jeśli to inna stacja niż aktualna
        if target_station_name:
            target_url = find_station_url(target_station_name, stations)
            currently_playing_url = mpc.get_current_url()
            
            # Wymuś powrót do stacji po zakończeniu newsów
            force_play = was_news_playing and not news_played_this_cycle

            if target_url and (force_play or target_url != currently_playing_url):
                logging.info(f"Changing station to: {target_station_name} (URL: {target_url})")
                mpc.play_url(target_url)
        
        was_news_playing = news_played_this_cycle
        time.sleep(10)

if __name__ == "__main__":
    try:
        main()
    except Exception as e:
        logging.critical(f"Daemon terminated due to a critical error: {e}", exc_info=True)
