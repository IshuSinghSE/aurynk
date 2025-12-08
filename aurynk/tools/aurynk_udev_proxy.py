#!/usr/bin/env python3
"""aurynk udev proxy

Runs as a per-user helper. Monitors udev (pyudev), broadcasts device add/remove
events to connected clients over a unix domain socket, and accepts commands to
start/stop scrcpy (and other host-side actions).

This script is intended to run on the host (outside the Flatpak sandbox).
Clients inside the Flatpak connect to `$XDG_RUNTIME_DIR/aurynk-udev.sock` and
receive newline-delimited JSON events and may send JSON commands.
"""

from __future__ import annotations

import asyncio
import json
import logging
import os
import subprocess
from pathlib import Path
from typing import Any, Dict, Set

import pyudev

LOG = logging.getLogger("aurynk_udev_proxy")
SOCKET_NAME = "aurynk-udev.sock"


class UdevProxyServer:
    def __init__(self, socket_path: Path):
        self.socket_path = socket_path
        self.clients: Set[asyncio.StreamWriter] = set()
        self.devices: Dict[str, Dict[str, Any]] = {}
        self.processes: Dict[str, asyncio.subprocess.Process] = {}
        self.loop = asyncio.get_event_loop()

        self.context = pyudev.Context()

    async def start(self):
        # Remove stale socket if present
        try:
            if self.socket_path.exists():
                self.socket_path.unlink()
        except Exception:
            LOG.exception("Failed removing stale socket")

        # Ensure parent dir exists
        self.socket_path.parent.mkdir(parents=True, exist_ok=True)

        # Populate initial device list from current udev state so clients
        # see devices already connected when they subscribe.
        try:
            for dev in self.context.list_devices(subsystem="usb"):
                try:
                    info = {
                        "action": "present",
                        "serial": dev.get("ID_SERIAL")
                        or dev.get("SERIAL")
                        or dev.device_node
                        or "",
                        "vendor_id": dev.get("ID_VENDOR_ID"),
                        "product_id": dev.get("ID_MODEL_ID"),
                        "properties": dict(dev.items()),
                    }
                    serial = info["serial"] or ""
                    if serial:
                        self.devices[serial] = info
                except Exception:
                    LOG.debug("Error enumerating device during startup", exc_info=True)
        except Exception:
            LOG.debug("Could not enumerate initial udev devices", exc_info=True)

        # Also query adb for connected devices and add them to the device map
        try:
            result = subprocess.run(
                ["adb", "devices", "-l"], capture_output=True, text=True, timeout=2
            )
            lines = result.stdout.strip().splitlines()
            for line in lines[1:]:
                if not line.strip():
                    continue
                parts = line.split()
                if len(parts) >= 2 and parts[1] == "device":
                    adb_serial = parts[0]
                    # Try to extract model/manufacturer from trailing info
                    props = {}
                    for p in parts[2:]:
                        if ":" in p:
                            k, v = p.split(":", 1)
                            props[k] = v
                    info = {
                        "action": "adb_present",
                        "serial": adb_serial,
                        "adb_props": props,
                        "vendor_id": None,
                        "product_id": None,
                        "properties": {},
                    }
                    self.devices[adb_serial] = info
        except Exception:
            LOG.debug("Could not enumerate adb devices at startup", exc_info=True)

            # schedule an initial adb rescan (async) to ensure adb-backed devices
            # are present in our device map and appear to subscribers.
            asyncio.ensure_future(self._rescan_adb())

        server = await asyncio.start_unix_server(self._handle_client, path=str(self.socket_path))

        # Set owner-only permissions on the socket
        try:
            self.socket_path.chmod(0o600)
        except Exception:
            LOG.exception("Failed to chmod socket")

        # Start udev observer in background thread via MonitorObserver
        monitor = pyudev.Monitor.from_netlink(self.context)
        monitor.filter_by(subsystem="usb")

        def _udev_callback(action, device):
            try:
                info = {
                    "action": action,
                    "serial": device.get("ID_SERIAL")
                    or device.get("SERIAL")
                    or device.device_node
                    or "",
                    "vendor_id": device.get("ID_VENDOR_ID"),
                    "product_id": device.get("ID_MODEL_ID"),
                    "properties": dict(device.items()),
                }
                self.loop.call_soon_threadsafe(self._on_device_event, info)
            except Exception:
                LOG.exception("Error in udev callback")

        observer = pyudev.MonitorObserver(monitor, callback=_udev_callback)
        observer.start()
        LOG.info("Udev observer started")

        LOG.info("Starting unix socket server at %s", self.socket_path)
        async with server:
            await server.serve_forever()

    def _on_device_event(self, info: Dict[str, Any]):
        # Update in-memory device state and broadcast
        serial = info.get("serial") or ""
        action = info.get("action")
        if action == "add":
            self.devices[serial] = info
        elif action == "remove":
            self.devices.pop(serial, None)
            # Kick off an adb rescan and broadcast the device event. The rescan
            # will add/remove adb-backed device entries and then we broadcast an
            # updated state to subscribers as needed.
            asyncio.ensure_future(self._rescan_adb())
            asyncio.ensure_future(self._broadcast({"type": "device", **info}))

    async def _broadcast(self, message: Dict[str, Any]):
        data = (json.dumps(message) + "\n").encode("utf-8")
        to_remove = []
        for w in list(self.clients):
            try:
                w.write(data)
                try:
                    await w.drain()
                except (ConnectionResetError, BrokenPipeError):
                    # client disconnected while we were writing; remove silently
                    LOG.debug("Client disconnected during write", exc_info=True)
                    try:
                        w.close()
                    except Exception:
                        pass
                    to_remove.append(w)
                    continue
            except Exception:
                LOG.debug("Failed writing to client, removing", exc_info=True)
                try:
                    w.close()
                except Exception:
                    pass
                to_remove.append(w)
        for w in to_remove:
            self.clients.discard(w)

    async def _rescan_adb(self):
        """Rescan adb for connected devices and update device map.

        This runs after udev events to pick up adb-backed devices (which may
        not be visible via udev properties), and broadcasts a 'state' update
        to subscribers when changes occur.
        """
        try:
            proc = await asyncio.create_subprocess_exec(
                "adb",
                "devices",
                "-l",
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
            )
            out, err = await asyncio.wait_for(proc.communicate(), timeout=3.0)
            text = out.decode("utf-8", errors="ignore")
            lines = text.strip().splitlines()
            new_adb = {}
            for line in lines[1:]:
                if not line.strip():
                    continue
                parts = line.split()
                if len(parts) >= 2 and parts[1] == "device":
                    adb_serial = parts[0]
                    props = {}
                    for p in parts[2:]:
                        if ":" in p:
                            k, v = p.split(":", 1)
                            props[k] = v
                    info = {
                        "action": "adb_present",
                        "serial": adb_serial,
                        "adb_props": props,
                        "vendor_id": None,
                        "product_id": None,
                        "properties": {},
                    }
                    new_adb[adb_serial] = info

            changed = False
            # Add or update adb entries
            for s, info in new_adb.items():
                if s not in self.devices or self.devices.get(s, {}).get("action") != "adb_present":
                    self.devices[s] = info
                    changed = True

            # Remove adb entries that disappeared
            for s in list(self.devices.keys()):
                if self.devices.get(s, {}).get("action") == "adb_present" and s not in new_adb:
                    self.devices.pop(s, None)
                    changed = True

            if changed:
                await self._broadcast({"type": "state", "devices": list(self.devices.values())})
        except Exception:
            LOG.debug("adb rescan failed", exc_info=True)

    async def _handle_client(self, reader: asyncio.StreamReader, writer: asyncio.StreamWriter):
        peer = writer.get_extra_info("peername")
        LOG.info("Client connected %s", peer)
        # Do not register client as a persistent subscriber until it
        # explicitly sends a 'subscribe' command. One-shot command
        # connections should not be treated as subscribers.

        try:
            while not reader.at_eof():
                line = await reader.readline()
                if not line:
                    break
                try:
                    req = json.loads(line.decode("utf-8"))
                except Exception:
                    await self._send(
                        writer, {"code": 1, "status": "error", "error": "invalid_json"}
                    )
                    continue

                # Handle commands
                if "cmd" in req:
                    # Special-case subscribe: client requests to receive events
                    if req.get("cmd") == "subscribe":
                        # Add to client list if not already
                        if writer not in self.clients:
                            self.clients.add(writer)
                        # Respond with current state (include devices)
                        # Return the current state and mark it explicitly as a
                        # 'state' message so subscribers inside the sandbox can
                        # detect and apply the initial device list.
                        resp = {
                            "code": 0,
                            "status": "ok",
                            "type": "state",
                            "devices": list(self.devices.values()),
                        }
                        if "id" in req:
                            resp["id"] = req["id"]
                        await self._send(writer, resp)
                        # continue reading; client stays connected to receive broadcasts
                        continue

                    resp = await self._handle_cmd(req)
                    if isinstance(resp, dict) and "id" in req and "id" not in resp:
                        resp = dict(resp)
                        resp["id"] = req["id"]
                    await self._send(writer, resp)
                else:
                    resp = {"code": 1, "status": "error", "error": "unknown_request"}
                    if "id" in req:
                        resp["id"] = req["id"]
                    await self._send(writer, resp)
        except Exception:
            LOG.exception("Client read loop error")
        finally:
            LOG.info("Client disconnected %s", peer)
            try:
                writer.close()
            except Exception:
                pass
            self.clients.discard(writer)

    async def _send(self, writer: asyncio.StreamWriter, msg: Dict[str, Any]):
        # Normalize status -> code
        if isinstance(msg, dict) and "code" not in msg and "status" in msg:
            if msg.get("status") == "ok":
                msg = dict(msg)
                msg["code"] = 0
            else:
                msg = dict(msg)
                msg.setdefault("code", 1)

        writer.write((json.dumps(msg) + "\n").encode("utf-8"))
        try:
            await writer.drain()
        except (ConnectionResetError, BrokenPipeError):
            # Expected when a one-shot client disconnects while we're
            # writing (or a subscriber went away). Handle silently.
            LOG.debug("Client disconnected while sending")
            try:
                writer.close()
            except Exception:
                pass
            self.clients.discard(writer)
        except Exception:
            LOG.exception("Failed sending message to client")

    async def _handle_cmd(self, req: Dict[str, Any]) -> Dict[str, Any]:
        cmd = req.get("cmd")
        if cmd == "ping":
            return {"code": 0, "status": "ok", "pong": True}
        if cmd == "status":
            procs = {s: {"pid": p.pid if p else None} for s, p in self.processes.items()}
            return {
                "code": 0,
                "status": "ok",
                "devices": list(self.devices.values()),
                "processes": procs,
            }

        if cmd == "start_mirror":
            serial = req.get("serial")
            options = req.get("options", {}) or {}
            if not serial:
                return {"code": 1, "status": "error", "error": "missing_serial"}
            if serial in self.processes:
                return {"code": 1, "status": "error", "error": "already_running"}
            # Launch scrcpy for the serial
            scrcpy_cmd = options.get("scrcpy_cmd") or "scrcpy"
            args = [scrcpy_cmd, "-s", serial]
            # Append any supplied args (careful: do not trust arbitrary shell input)
            extra_args = options.get("args")
            if isinstance(extra_args, list):
                args.extend(extra_args)

            try:
                proc = await asyncio.create_subprocess_exec(
                    *args, stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.PIPE
                )
            except Exception as e:
                LOG.exception("Failed to start scrcpy")
                return {"code": 1, "status": "error", "error": "start_failed", "detail": str(e)}

            self.processes[serial] = proc

            # Monitor process exit
            asyncio.ensure_future(self._monitor_process(serial, proc))
            return {"code": 0, "status": "ok", "pid": proc.pid}

        if cmd == "stop_mirror":
            serial = req.get("serial")
            if not serial:
                return {"code": 1, "status": "error", "error": "missing_serial"}
            proc = self.processes.get(serial)
            if not proc:
                return {"code": 1, "status": "error", "error": "not_running"}
            try:
                proc.terminate()
                try:
                    await asyncio.wait_for(proc.wait(), timeout=2.0)
                except asyncio.TimeoutError:
                    proc.kill()
                    await proc.wait()
            except Exception as e:
                LOG.exception("Error stopping process")
                return {"code": 1, "status": "error", "error": "stop_failed", "detail": str(e)}
            # process monitor will remove from dict
            return {"code": 0, "status": "ok"}

        return {"code": 1, "status": "error", "error": "unknown_cmd"}

    async def _monitor_process(self, serial: str, proc: asyncio.subprocess.Process):
        try:
            await proc.wait()
            LOG.info("Process for %s exited with %s", serial, proc.returncode)
        except Exception:
            LOG.exception("Error waiting for process")
        finally:
            self.processes.pop(serial, None)
            await self._broadcast(
                {
                    "type": "process",
                    "action": "exit",
                    "serial": serial,
                    "returncode": proc.returncode,
                }
            )


def main():
    logging.basicConfig(level=logging.INFO)
    xdg = os.environ.get("XDG_RUNTIME_DIR")
    if not xdg:
        raise SystemExit("XDG_RUNTIME_DIR not set")
    sock = Path(xdg) / SOCKET_NAME
    server = UdevProxyServer(sock)
    try:
        asyncio.run(server.start())
    except KeyboardInterrupt:
        LOG.info("Interrupted")


if __name__ == "__main__":
    main()
