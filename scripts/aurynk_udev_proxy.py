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
        self.loop = None  # Will be set when async context starts
        self.event_queue = None  # Will be created in async context
        self.last_added_device = None  # Track most recently added device for remove correlation

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
        LOG.info("Udev monitor created with subsystem=usb filter")

        def _udev_callback(device):
            LOG.debug(f"Udev callback triggered: device={device}")
            # pyudev may call the observer callback with a single `device`
            # argument (the MonitorObserver implementation varies), so be
            # tolerant of different signatures. Extract the action in a
            # robust way and normalize it to lowercase strings like
            # 'add'/'remove'/'change'.
            try:
                # Prefer attribute access (pyudev Device.action), fall back
                # to environment property names.
                action = None
                try:
                    action = getattr(device, "action", None)
                except Exception:
                    action = None

                if not action:
                    try:
                        action = device.get("ACTION")
                    except Exception:
                        action = None

                if not action:
                    # Some monitor implementations pass a single string
                    # representing the action instead of a Device object.
                    # If that's the case, coerce accordingly.
                    if isinstance(device, str):
                        # Called as _udev_callback(action)
                        action = device
                        device = None

                action = str(action).lower() if action is not None else "present"
                LOG.info(
                    f"Udev callback processing: action={action}, device_type={type(device).__name__}"
                )

                serial = ""
                vendor = None
                product = None
                props = {}
                if device is not None:
                    try:
                        serial = (
                            device.get("ID_SERIAL")
                            or device.get("SERIAL")
                            or getattr(device, "device_node", None)
                            or ""
                        )
                    except Exception:
                        serial = ""
                    try:
                        vendor = device.get("ID_VENDOR_ID")
                    except Exception:
                        vendor = None
                    try:
                        product = device.get("ID_MODEL_ID")
                    except Exception:
                        product = None
                    try:
                        props = dict(device.items())
                    except Exception:
                        props = {}

                info = {
                    "action": action,
                    "serial": serial,
                    "vendor_id": vendor,
                    "product_id": product,
                    "properties": props,
                }

                LOG.info(
                    f"Udev callback info: action={action}, serial='{serial}', vendor={vendor}, product={product}"
                )

                # Put event in queue for async processing
                # Use asyncio.run_coroutine_threadsafe to properly schedule the put operation
                LOG.info("Putting event in queue via run_coroutine_threadsafe")
                asyncio.run_coroutine_threadsafe(self.event_queue.put(info), self.loop)
            except Exception:
                LOG.exception("Error in udev callback")

        observer = pyudev.MonitorObserver(monitor, callback=_udev_callback)
        observer.start()
        LOG.info("Udev observer started")

        # Get the running event loop and create queue in async context
        self.loop = asyncio.get_running_loop()
        self.event_queue = asyncio.Queue()
        LOG.info("Event queue created in async context with running loop")

        # Start background task to process device events from the queue
        asyncio.create_task(self._process_event_queue())

        LOG.info("Starting unix socket server at %s", self.socket_path)
        async with server:
            await server.serve_forever()

    async def _process_event_queue(self):
        """Process device events from the queue continuously."""
        LOG.info("Event queue processor started")
        while True:
            try:
                LOG.info("Waiting for event from queue...")
                info = await self.event_queue.get()
                LOG.info(f"Processing queued event: {info.get('action')}")
                await self._on_device_event_async(info)
                self.event_queue.task_done()
            except Exception:
                LOG.exception("Error processing event from queue")

    async def _on_device_event_async(self, info: Dict[str, Any]):
        try:
            # Update in-memory device state and broadcast
            serial = info.get("serial") or ""
            action = info.get("action")

            LOG.info(f"_on_device_event called: action={action}, serial='{serial}'")

            # For device identification, prefer ID_SERIAL, but fall back to a composite
            # key if serial is empty or just a device path (like /dev/bus/usb/X/Y)
            device_key = serial
            if not device_key or device_key.startswith("/dev/"):
                # Use vendor_id:product_id as key for devices without proper serial
                vendor = info.get("vendor_id")
                product = info.get("product_id")
                LOG.debug(f"Serial empty or device path, vendor={vendor}, product={product}")
                if vendor and product:
                    device_key = f"usb:{vendor}:{product}"
                    LOG.debug(f"Using composite key: {device_key}")
                else:
                    # For remove events without identifiers, use the last added device
                    if action in ("remove", "unbind"):
                        if self.last_added_device:
                            LOG.info(
                                f"Remove event without identifier - removing last added: {self.last_added_device}"
                            )
                            # Remove the last added device and broadcast it
                            removed_info = self.devices.pop(self.last_added_device, {})
                            if removed_info:
                                removed_info["action"] = "remove"
                                await self._broadcast({"type": "device", **removed_info})
                            else:
                                # Fallback: broadcast generic remove
                                await self._broadcast(
                                    {
                                        "type": "device",
                                        "action": "remove",
                                        "serial": self.last_added_device,
                                    }
                                )
                            self.last_added_device = None
                            asyncio.ensure_future(self._rescan_adb())
                            return
                        else:
                            LOG.info(
                                "Remove event without identifier and no last device - triggering state refresh"
                            )
                            # Broadcast a generic remove event to trigger full state refresh
                            await self._broadcast(
                                {"type": "device", "action": "remove", "serial": ""}
                            )
                            asyncio.ensure_future(self._rescan_adb())
                            return
                    else:
                        # Skip add events with no usable identifier
                        LOG.debug(
                            f"Skipping add event with no identifier: action={action}, serial='{serial}'"
                        )
                        return

            LOG.info(f"Udev event: action={action}, device_key={device_key}")
            # For both add and remove (and similar udev actions) update our
            # in-memory state, trigger an adb rescan and broadcast a device
            # notification so subscribers update promptly.
            # Treat 'add' and 'bind' as device connection
            # Treat 'remove' and 'unbind' as device disconnection
            if action in ("add", "bind"):
                self.devices[device_key] = info
                self.last_added_device = device_key  # Remember for remove correlation
                LOG.info(f"Device added/bound: {device_key}")
                # Normalize action to 'add' for client consistency
                info["action"] = "add"
                # Rescan adb to pick up adb-backed devices that may be present
                # and broadcast an event so clients refresh their UI.
                asyncio.ensure_future(self._rescan_adb())
                await self._broadcast({"type": "device", **info})
                LOG.info(f"Broadcasted add event for {device_key}")
            elif action in ("remove", "unbind"):
                self.devices.pop(device_key, None)
                LOG.info(f"Device removed/unbound: {device_key}")
                # Normalize action to 'remove' for client consistency
                info["action"] = "remove"
                asyncio.ensure_future(self._rescan_adb())
                await self._broadcast({"type": "device", **info})
                LOG.info(f"Broadcasted remove event for {device_key}")
        except Exception:
            LOG.exception("Error in _on_device_event_async")

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
