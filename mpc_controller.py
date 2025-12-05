#!/usr/bin/env python3
# Copyright (c) 2025 Daszkan (Jacek S.)
#
# This software is released under the MIT License.
# https://opensource.org/licenses/MIT
import subprocess
import logging
from pathlib import Path

LOG_PATH = Path.home() / ".config/radio-scheduler/mpc_controller.log"

# Konfiguracja dedykowanego loggera dla tego modułu
logger = logging.getLogger(__name__)
if not logger.handlers:
    logger.setLevel(logging.ERROR)
    handler = logging.FileHandler(LOG_PATH)
    formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
    handler.setFormatter(formatter)
    logger.addHandler(handler)

class MPCController:
    def _run_command(self, command, check=False):
        try:
            result = subprocess.run(command, check=check, capture_output=True, text=True)
            if check and result.returncode != 0:
                logger.error(f"Polecenie '{' '.join(command)}' nie powiodło się: {result.stderr.strip()}")
                return None
            return result
        except FileNotFoundError:
            logger.error("Polecenie 'mpc' nie zostało znalezione. Upewnij się, że jest zainstalowane i w ścieżce PATH.")
            return None
        except Exception as e:
            logger.error(f"Niespodziewany błąd podczas uruchamiania polecenia '{' '.join(command)}': {e}")
            return None

    def get_volume(self):
        result = self._run_command(["mpc", "volume"])
        if result and result.stdout:
            try:
                return int(result.stdout.split()[-1].strip("%"))
            except (ValueError, IndexError):
                logger.error(f"Nie można przetworzyć głośności z wyjścia MPC: {result.stdout}")
        return 50  # Domyślna głośność

    def set_volume(self, volume):
        volume = max(0, min(100, volume))
        self._run_command(["mpc", "volume", str(volume)], check=True)

    def get_current(self):
        result = self._run_command(["mpc", "current"])
        return result.stdout.strip() if result and result.stdout else "–"

    def get_current_url(self):
        result = self._run_command(["mpc", "current", "-f", "%file%"])
        return result.stdout.strip() if result and result.stdout else None

    def play_url(self, url):
        if self.clear():
            if self.add(url):
                return self.play()
        return False

    def clear(self):
        return self._run_command(["mpc", "clear"], check=True) is not None

    def add(self, url):
        return self._run_command(["mpc", "add", url], check=True) is not None

    def play(self):
        return self._run_command(["mpc", "play"], check=True) is not None

    def stop(self):
        return self._run_command(["mpc", "stop"], check=True) is not None