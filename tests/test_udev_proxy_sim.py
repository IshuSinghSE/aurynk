#!/usr/bin/env python3
"""Simple simulator for udev proxy used in tests."""

import json
import socket
import threading
import time
from pathlib import Path


def run_simulator(sockpath: Path, ready_evt: threading.Event):
    if sockpath.exists():
        sockpath.unlink()
    srv = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
    srv.bind(str(sockpath))
    srv.listen(1)
    srv.settimeout(5.0)
    ready_evt.set()
    try:
        conn, _ = srv.accept()
    except Exception:
        srv.close()
        return

    f = conn.makefile("rwb")
    # Send initial state
    f.write((json.dumps({"type": "state", "devices": []}) + "\n").encode())
    f.flush()

    # Read a command
    line = f.readline()
    if not line:
        conn.close()
        srv.close()
        return
    req = json.loads(line.decode())
    rid = req.get("id")
    # respond with ok
    resp = {"code": 0, "status": "ok", "result": "pong"}
    if rid:
        resp["id"] = rid
    f.write((json.dumps(resp) + "\n").encode())
    f.flush()

    # Send a device add event after a small delay
    time.sleep(0.1)
    ev = {
        "type": "device",
        "action": "add",
        "serial": "TEST1234",
        "vendor_id": "0x1234",
        "product_id": "0xabcd",
    }
    f.write((json.dumps(ev) + "\n").encode())
    f.flush()

    # Keep connection open for a short while
    time.sleep(0.5)
    conn.close()
    srv.close()
