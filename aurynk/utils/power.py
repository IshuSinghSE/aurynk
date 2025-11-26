import threading
import time

from aurynk.utils.logger import get_logger

logger = get_logger("PowerMonitor")


class PowerMonitor:
    """Monitors system suspend/resume and triggers callbacks."""

    def __init__(self):
        self._callbacks = {"sleep": [], "resume": []}
        self._running = False
        self._thread = None

    def register_callback(self, event, callback):
        if event in self._callbacks:
            self._callbacks[event].append(callback)

    def start(self):
        if self._running:
            return
        self._running = True
        self._thread = threading.Thread(target=self._monitor, daemon=True)
        self._thread.start()

    def stop(self):
        self._running = False
        if self._thread:
            self._thread.join(timeout=1)

    def _monitor(self):
        # Use /run/systemd/inhibit/sleep or logind signals if available, else poll /proc/uptime
        last_uptime = self._get_uptime()
        while self._running:
            time.sleep(2)
            uptime = self._get_uptime()
            if uptime is not None and last_uptime is not None:
                # If uptime decreased, system suspended and resumed
                if uptime < last_uptime:
                    logger.info("System resume detected")
                    for cb in self._callbacks["resume"]:
                        try:
                            cb()
                        except Exception as e:
                            logger.error(f"Resume callback error: {e}")
                elif uptime - last_uptime > 60:
                    logger.info("System sleep detected")
                    for cb in self._callbacks["sleep"]:
                        try:
                            cb()
                        except Exception as e:
                            logger.error(f"Sleep callback error: {e}")
            last_uptime = uptime

    def _get_uptime(self):
        try:
            with open("/proc/uptime", "r") as f:
                return float(f.read().split()[0])
        except Exception:
            return None
