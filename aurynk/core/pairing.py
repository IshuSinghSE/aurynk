"""ADB pairing management."""

import ipaddress
import subprocess

from aurynk.utils.adb_utils import get_adb_path
from aurynk.utils.logger import get_logger

logger = get_logger("PairingManager")


class PairingManager:
    """Handles ADB pairing operations."""

    def pair_with_code(self, ip: str, port: str, code: str) -> bool:
        """
        Pair with a device using IP, port, and pairing code.

        Args:
            ip (str): The IPv4 address of the device.
            port (str): The port number for pairing.
            code (str): The pairing code displayed on the device.

        Returns:
            bool: True if pairing was successful, False otherwise.
        """
        # Validate IPv4 address
        try:
            ip_obj = ipaddress.ip_address(ip)
            if not isinstance(ip_obj, ipaddress.IPv4Address):
                logger.error(f"Invalid IPv4 address: {ip}")
                return False
        except ValueError:
            logger.error(f"Invalid IP address format: {ip}")
            return False

        # Validate port (basic check)
        if not port.isdigit():
            logger.error(f"Invalid port: {port}")
            return False

        adb_path = get_adb_path()
        cmd = [adb_path, "pair", f"{ip}:{port}", code]

        try:
            # Using a default timeout of 10 seconds, similar to other parts of the app
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=10)

            if result.returncode == 0:
                logger.info(f"Successfully paired with {ip}:{port}")
                return True
            else:
                logger.warning(
                    f"Pairing failed for {ip}:{port}. "
                    f"Output: {result.stdout.strip()} {result.stderr.strip()}"
                )
                return False

        except subprocess.TimeoutExpired:
            logger.error(f"Pairing timed out for {ip}:{port}")
            return False
        except Exception as e:
            logger.error(f"Unexpected error during pairing: {e}")
            return False
