import _thread
import argparse
import importlib.metadata
import io
import logging
import os
import random
import string
import subprocess
import sys
import time
from os import get_terminal_size

import qrcode
from rich.logging import RichHandler
from zeroconf import IPVersion, ServiceBrowser, ServiceStateChange, Zeroconf


def get_code(n: int):
    return "".join(random.choices(string.ascii_letters, k=n))


SIZE = 5
NAME = "ADB_WIFI_" + get_code(SIZE)
PASSWORD = get_code(SIZE)
TYPES = ["_adb-tls-connect._tcp.local.", "_adb-tls-pairing._tcp.local."]
ADB_PATH = "adb"
QR_SCALE = 10
QR_BORDER = 1
TCPIP_PORT = 5555
USE_PORT = 0

parser = argparse.ArgumentParser()
parser.add_argument(
    "--adb-path",
    default=ADB_PATH,
    help=f"Path to `adb` platform-tool. Defaults to {repr(ADB_PATH)}.",
)
parser.add_argument(
    "--tcpip-port",
    default=TCPIP_PORT,
    type=int,
    help=f"Port for doing `adb tcpip`. See `--do-tcpip` flag. Defaults to {repr(TCPIP_PORT)}.",
)
parser.add_argument(
    "--use-port",
    default=USE_PORT,
    type=int,
    help=f"Specify port for doing `adb pair` and `adb connect` instead of auto-detecting it. Defaults to {repr(USE_PORT)}.",
)
parser.add_argument(
    "--qr-scale",
    default=QR_SCALE,
    type=int,
    help=f"(SIXEL ONLY) QR code image scale. Defaults to {repr(QR_SCALE)}.",
)
parser.add_argument(
    "--qr-border",
    default=QR_BORDER,
    type=int,
    help=f"QR code border size. Defaults to {repr(QR_BORDER)}.",
)
parser.add_argument("--debug", action="store_true", help="Enable debug logs.")
parser.add_argument(
    "--as-sixel",
    action="store_true",
    help="(EXPERIMENTAL) Use Sixel graphics. Currently not supported on Windows.",
)
parser.add_argument(
    "--only-connect",
    action="store_true",
    help="Only connect to the device, don't pair.",
)
parser.add_argument(
    "--do-tcpip",
    action="store_true",
    help="After connecting do `adb tcpip` on specified port.",
)
parser.add_argument(
    "--connect-tcpip",
    action="store_true",
    help="Detects device IP on startup and tries to connect to it with TCPIP_PORT as the port.",
)
parser.add_argument(
    "-V",
    "--version",
    action="version",
    version=importlib.metadata.version("lyto"),
    help="Show package version.",
)

cli_args = parser.parse_args()
ADB_PATH = cli_args.adb_path
QR_SCALE = cli_args.qr_scale
QR_BORDER = cli_args.qr_border
USE_PORT = cli_args.use_port
TCPIP_PORT = cli_args.tcpip_port

logging.basicConfig(
    level=logging.DEBUG if cli_args.debug else logging.INFO,
    format="%(message)s",
    datefmt="[%X]",
    handlers=[RichHandler(markup=True)],
)

log = logging.getLogger(__name__)
device_ports = []

log.debug(f"{NAME=}")
log.debug(f"{PASSWORD=}")


def generate_code(name: str, password: str):
    return f"WIFI:T:ADB;S:{name};P:{password};;"


def ascii_qr_code(text: str):
    qr = qrcode.QRCode(border=QR_BORDER, box_size=QR_SCALE, version=1)
    qr.add_data(text)

    if cli_args.as_sixel:
        import sixel

        log.debug("Outputting QR code as Sixel graphics")
        file = io.BytesIO()

        img = qr.make_image(back_color="white", fill_color="black")
        img.save(file)

        writer = sixel.converter.SixelConverter(file, chromakey=True)

        return writer.getvalue()

    file = io.StringIO()
    qr.print_ascii(invert=True, out=file)
    file.seek(0)
    x, y = get_terminal_size()
    pos = line_c = 0

    for line in file.readlines():
        file.seek(pos)
        file.write((x - len(line)) // 2 * " " + line)
        pos = file.tell()
        line_c += 1

    file.seek(0)
    return (y - line_c) // 2 * "\n" + file.read()


def _debug_info_pc(out: subprocess.CompletedProcess):
    log.debug(f"{out.stderr=}")
    log.debug(f"{out.stdout=}")


def forceful_exit():
    log.info("[italic yellow]Exiting...[/]")
    _thread.interrupt_main()


def pair_device(address: str, port: int, password: str):
    log.info("[italic yellow]Pairing...[/]")
    args = [ADB_PATH, "pair", f"{address}:{port}", password]
    log.debug("Args for pairing command: %s", args)
    out = subprocess.run(args, capture_output=True)

    if out.returncode != 0:
        log.critical("[red bold]Pairing failed.[/]")
        _debug_info_pc(out)
        return

    log.info("[bold green]Paired[/].")


def connect_device(address: str, port: int):
    log.info("[italic yellow]Connecting...[/]")
    args = [ADB_PATH, "connect", f"{address}:{port}"]
    log.debug("Args for connecting command: %s", args)
    out = subprocess.run(args, capture_output=True)

    if out.returncode != 0:
        log.critical("[red bold]Connecting failed.[/]")
        _debug_info_pc(out)
        return

    log.info("[bold green]Connected[/].")
    if not cli_args.do_tcpip:
        forceful_exit()


def tcpip_device(port: int):
    log.info(f"[italic yellow]Activating TCP IP on port {port}...[/]")
    args = [ADB_PATH, "tcpip", f"{port}"]
    log.debug("Args for tcpip command: %s", args)
    out = subprocess.run(args, capture_output=True)

    if out.returncode != 0:
        log.critical("[red bold]TCP IP activation failed.[/]")
        _debug_info_pc(out)
        return

    log.info("[bold green]Activated[/].")
    forceful_exit()


def on_service_state_change(
    zeroconf: Zeroconf,
    service_type: str,
    name: str,
    state_change: ServiceStateChange,
) -> None:
    log.debug("Running on_service_state_change listener.")
    if state_change is ServiceStateChange.Added:
        info = zeroconf.get_service_info(service_type, name)
        log.debug(f"{info=}")
        if not info:
            return

        log.debug(f"{device_ports}")
        log.debug(f"{info.type=}")
        log.debug(f"{info.port=}")
        log.debug(f"{info.parsed_addresses()=}")

        addr = info.parsed_addresses()[0]

        if service_type == "_adb-tls-pairing._tcp.local.":
            if not device_ports:
                return

            if cli_args.use_port == 0:
                pair_port = info.port or 5555
                connect_port = device_ports[0]
            else:
                pair_port = connect_port = cli_args.use_port

            if not cli_args.only_connect:
                pair_device(addr, pair_port, PASSWORD)

            connect_device(addr, connect_port)

            if cli_args.do_tcpip:
                tcpip_device(TCPIP_PORT)
        elif service_type == "_adb-tls-connect._tcp.local.":
            if cli_args.connect_tcpip:
                connect_device(addr, TCPIP_PORT)
                tcpip_device(TCPIP_PORT)

            device_ports.append(info.port)


def main() -> int:
    if cli_args.as_sixel and os.name == "nt":
        log.error(
            "[red bold]--as-sixel flag is currently not supported on Windows.[/]"
        )
        sys.exit(1)

    print("\033[?1049h", end="")
    print(ascii_qr_code(generate_code(NAME, PASSWORD)))

    zc = Zeroconf(ip_version=IPVersion.V4Only)

    ServiceBrowser(
        zc=zc,
        type_=TYPES,
        handlers=[on_service_state_change],
    )

    try:
        while True:
            time.sleep(0.1)
    except KeyboardInterrupt:
        pass
    finally:
        print("\033[?1049l", end="")
        zc.close()
        return 0
