"""Client for aurynk udev proxy socket.

Provides a small, synchronous-friendly client that:
- subscribes to events via a persistent connection (calls callback on each event)
- sends short-lived commands (start_mirror/stop_mirror/status) over new connections

This keeps the app-side code simple and avoids multiplexing complexity.
"""

import json
import os
import socket
import threading
import time
from pathlib import Path
from typing import Callable, Optional

from aurynk.utils.logger import get_logger

logger = get_logger("UdevProxyClient")

_REQ_LOCK = threading.Lock()
_REQ_COUNTER = 0

SOCKET_NAME = "aurynk-udev.sock"


def _socket_path() -> Path:
    xdg = os.environ.get("XDG_RUNTIME_DIR")
    if not xdg:
        raise RuntimeError("XDG_RUNTIME_DIR not set")
    return Path(xdg) / SOCKET_NAME


class UdevProxyClient:
    def __init__(self):
        self._event_thread: Optional[threading.Thread] = None
        self._stop_event = threading.Event()
        self._callbacks = []

    def subscribe(self, callback: Callable[[dict], None]):
        """Start a background listener and deliver events to callback.

        The callback is called for every JSON message received from the helper.
        """
        self._callbacks.append(callback)
        if self._event_thread is None:
            self._event_thread = threading.Thread(target=self._run_event_loop, daemon=True)
            self._event_thread.start()

    def _run_event_loop(self):
        sockpath = str(_socket_path())
        backoff = 0.5
        while not self._stop_event.is_set():
            try:
                with socket.socket(socket.AF_UNIX, socket.SOCK_STREAM) as s:
                    logger.debug("Attempting to connect to udev proxy socket %s", sockpath)
                    s.connect(sockpath)
                    logger.info("Connected to udev proxy")
                    backoff = 0.5
                    f = s.makefile("rb")
                    # Send explicit subscribe command so server will send state and keep connection
                    subscribe = {"cmd": "subscribe"}
                    b = (json.dumps(subscribe) + "\n").encode("utf-8")
                    try:
                        s.sendall(b)
                    except Exception:
                        # if we can't write, close and retry
                        logger.debug("Failed to send subscribe, will retry")
                        continue
                    while not self._stop_event.is_set():
                        line = f.readline()
                        if not line:
                            break
                        try:
                            msg = json.loads(line.decode("utf-8"))
                        except Exception:
                            continue
                        for cb in list(self._callbacks):
                            try:
                                cb(msg)
                            except Exception:
                                pass
            except FileNotFoundError:
                # helper not running yet; sleep and retry
                logger.debug("Udev proxy socket not found: %s", sockpath)
                self._stop_event.wait(backoff)
                backoff = min(backoff * 2, 8.0)
            except ConnectionRefusedError:
                logger.debug("Connection refused to udev proxy socket %s", sockpath)
                self._stop_event.wait(backoff)
                backoff = min(backoff * 2, 8.0)
            except Exception:
                logger.exception("Unexpected error in udev proxy event loop")
                self._stop_event.wait(backoff)
                backoff = min(backoff * 2, 8.0)

    def stop(self):
        self._stop_event.set()
        if self._event_thread:
            self._event_thread.join(timeout=1.0)
            self._event_thread = None

    def send_command(self, cmd: dict, timeout: float = 5.0) -> dict:
        """Send one-shot command and return response.

        The helper responds with a single JSON line and closes.
        """
        # Attach a request id if not provided
        if "id" not in cmd:
            # simple monotonic id
            global _REQ_COUNTER
            with _REQ_LOCK:
                _REQ_COUNTER += 1
                req_id = f"{int(time.time())}-{_REQ_COUNTER}"
            cmd = dict(cmd)
            cmd["id"] = req_id
        else:
            req_id = cmd["id"]

        sockpath = str(_socket_path())
        with socket.socket(socket.AF_UNIX, socket.SOCK_STREAM) as s:
            s.settimeout(timeout)
            s.connect(sockpath)
            b = (json.dumps(cmd) + "\n").encode("utf-8")
            s.sendall(b)
            f = s.makefile("rb")
            # Read lines until we find matching id or timeout
            time.time()
            while True:
                line = f.readline()
                if not line:
                    raise RuntimeError("no response")
                try:
                    resp = json.loads(line.decode("utf-8"))
                except Exception:
                    continue
                # If response has id, match it; otherwise accept it as notification
                if "id" in resp:
                    if resp["id"] != req_id:
                        # not ours, continue reading
                        continue
                    # structured response: check code
                    code = resp.get("code", None)
                    if code is None:
                        # legacy ok
                        return resp
                    if code == 0:
                        return resp
                    else:
                        raise RuntimeError(f"error from helper: {resp.get('error')}")
                else:
                    # Unidentified response - return it
                    return resp
