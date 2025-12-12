#!/usr/bin/env python3
"""RadioScheduler Daemon: A background process to manage radio station playback based on a schedule."""
# Copyright (c) 2025 Daszkan (Jacek)
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
    while True:
        config = load_config()
        stations = config.get("stations", [])
        sched = config.get("schedule", {})
        now = datetime.now()
        weekday = now.strftime("%a").lower()[:3]
        current_time_str = now.strftime("%H:%M")        

        target_station_name = None
        
        # Sprawdź flagę "bez newsów na dziś"
        no_news_today = NO_NEWS_TODAY_LOCK.exists() and NO_NEWS_TODAY_LOCK.read_text().strip() == str(now.date())

        # News breaks (advanced first)
        news_cfg = sched.get("news_breaks", {})
        news_played_this_cycle = False
        if not no_news_today and news_cfg.get("enabled", True):
            offset = news_cfg.get("start_minute_offset", 0)
            if news_cfg.get("use_advanced", False):
                for rule in news_cfg.get("advanced", []) or []:
                    if weekday in rule["days"]:
                        start = datetime.strptime(rule["from"], "%H:%M").time()
                        end = datetime.strptime(rule["to"], "%H:%M").time()
                        if start <= now.time() <= end:
                            # Calculate next news time with offset
                            base = datetime.combine(now.date(), start)
                            minutes_since_start = (now - base).total_seconds() // 60
                            next_news = base + timedelta(minutes=((minutes_since_start // rule["interval_minutes"] + 1) * rule["interval_minutes"]))
                            next_news = next_news.replace(minute=offset if offset else next_news.minute)
                            if now >= next_news and now < next_news + timedelta(minutes=rule.get("duration_minutes", 8)):
                                url = find_station_url(rule["station"], stations)
                                target_station_name = rule["station"]
                                news_played_this_cycle = True
                                break # Przerwij pętlę reguł newsów
            else:
                simple = news_cfg.get("simple", {})
                # Domyślne dni dla trybu prostego, jeśli nie zdefiniowano
                days = simple.get("days", ["mon","tue","wed","thu","fri","sat","sun"])
                if weekday in days and simple.get("station"):
                    if "from" in simple and "to" in simple:
                        start = datetime.strptime(simple.get("from", "00:00"), "%H:%M").time()
                        end = datetime.strptime(simple["to"], "%H:%M").time()
                        if start <= now.time() <= end:
                            interval = simple.get("interval_minutes", 30)
                            duration = simple.get("duration_minutes", 8)
                            base = datetime.combine(now.date(), start)
                            minutes_since_start = (now - base).total_seconds() // 60
                            next_news = base + timedelta(minutes=((minutes_since_start // interval + 1) * interval))
                            next_news = next_news.replace(minute=offset if offset else next_news.minute)
                            if now >= next_news and now < next_news + timedelta(minutes=duration):
                                url = find_station_url(simple["station"], stations)
                                target_station_name = simple["station"]
                                news_played_this_cycle = True
            
            if news_played_this_cycle:
                pass # Mamy już stację z newsów

        # Weekly schedule
        if not target_station_name and not MANUAL_OVERRIDE_LOCK.exists():
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

            if target_url and target_url != currently_playing_url:
                logging.info(f"Changing station to: {target_station_name} (URL: {target_url})")
                mpc.play_url(target_url)
        
        if news_played_this_cycle:
            time.sleep(60) # Po newsach poczekaj minutę

        time.sleep(10)

if __name__ == "__main__":
    try:
        main()
    except Exception as e:
        logging.critical(f"Daemon terminated due to a critical error: {e}", exc_info=True)
