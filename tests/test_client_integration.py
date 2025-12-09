#!/usr/bin/env python3
"""Integration test for UdevProxyClient using the simulator."""

import os
import tempfile
import threading
import time
from pathlib import Path

from aurynk.services.udev_proxy_client import UdevProxyClient


def test_client_subscribe_and_command():
    tmp = Path(tempfile.mkdtemp())
    os.environ["XDG_RUNTIME_DIR"] = str(tmp)
    sock = tmp / "aurynk-udev.sock"

    # start simulator
    ready = threading.Event()
    from tests.test_udev_proxy_sim import run_simulator

    t = threading.Thread(target=run_simulator, args=(sock, ready), daemon=True)
    t.start()
    ready.wait(timeout=2.0)

    client = UdevProxyClient()
    msgs = []

    def cb(m):
        msgs.append(m)

    client.subscribe(cb)

    # send a ping command
    resp = client.send_command({"cmd": "ping"}, timeout=2.0)
    assert resp.get("code") == 0

    # wait for device event
    timeout = time.time() + 2.0
    while time.time() < timeout and not any(m.get("type") == "device" for m in msgs):
        time.sleep(0.05)

    assert any(m.get("type") == "device" and m.get("serial") == "TEST1234" for m in msgs)

    client.stop()
