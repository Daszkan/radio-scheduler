#!/usr/bin/env python3
# Copyright (c) 2025 - 2026 Daszkan (Jacek S.)
#
# This software is released under the MIT License.
# https://opensource.org/licenses/MIT
import subprocess
import logging
import socket
from pathlib import Path

LOG_PATH = Path.home() / ".config/radio-scheduler/mpc_controller.log"

# Konfiguracja dedykowanego loggera dla tego modułu
logger = logging.getLogger(__name__)
if not logger.handlers:
    # Ensure the directory exists
    Path(LOG_PATH).parent.mkdir(parents=True, exist_ok=True)
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
            # Check for connection error even if stdout is present
            if result.returncode != 0 and "connection" in result.stderr.lower():
                return None
            try:
                return int(result.stdout.split()[-1].strip("%"))
            except (ValueError, IndexError):
                logger.error(f"Nie można przetworzyć głośności z wyjścia MPC: {result.stdout}")
        return None # Zwróć None, jeśli nie można pobrać głośności

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

    def get_status_dict(self):
        """Connects to MPD via socket to get raw status (bitrate, audio format)."""
        try:
            # Connect to MPD (localhost:6600 is default)
            with socket.create_connection(("localhost", 6600), timeout=0.1) as s:
                s.recv(1024) # Skip initial greeting (OK MPD ...)
                s.sendall(b"status\nclose\n")
                response = b""
                while True:
                    chunk = s.recv(4096)
                    if not chunk: break
                    response += chunk
                
                status = {}
                for line in response.decode('utf-8', errors='ignore').splitlines():
                    if ':' in line:
                        key, val = line.split(':', 1)
                        status[key.strip()] = val.strip()
                return status
        except Exception:
            return {}