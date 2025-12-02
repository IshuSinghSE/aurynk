import subprocess
import unittest
from unittest.mock import MagicMock, patch

from aurynk.core.pairing import PairingManager


class TestPairingManager(unittest.TestCase):
    def setUp(self):
        self.pairing_manager = PairingManager()

    @patch("aurynk.core.pairing.subprocess.run")
    def test_pair_with_code_success(self, mock_run):
        """Test successful pairing."""
        mock_run.return_value = MagicMock(returncode=0, stdout="Success", stderr="")

        result = self.pairing_manager.pair_with_code("192.168.1.5", "5555", "123456")

        self.assertTrue(result)
        mock_run.assert_called_once()
        args, kwargs = mock_run.call_args
        self.assertIn("pair", args[0])
        self.assertIn("192.168.1.5:5555", args[0])
        self.assertIn("123456", args[0])

    @patch("aurynk.core.pairing.subprocess.run")
    def test_pair_with_code_failure(self, mock_run):
        """Test failed pairing (e.g. wrong code)."""
        mock_run.return_value = MagicMock(returncode=1, stdout="", stderr="Failed")

        result = self.pairing_manager.pair_with_code("192.168.1.5", "5555", "123456")

        self.assertFalse(result)

    @patch("aurynk.core.pairing.subprocess.run")
    def test_pair_with_code_timeout(self, mock_run):
        """Test timeout during pairing."""
        mock_run.side_effect = subprocess.TimeoutExpired(cmd="adb pair", timeout=10)

        result = self.pairing_manager.pair_with_code("192.168.1.5", "5555", "123456")

        self.assertFalse(result)

    def test_pair_with_code_invalid_ip(self):
        """Test invalid IP address format."""
        result = self.pairing_manager.pair_with_code("invalid-ip", "5555", "123456")
        self.assertFalse(result)

    def test_pair_with_code_ipv6(self):
        """Test IPv6 address (should be rejected based on IPv4 requirement)."""
        result = self.pairing_manager.pair_with_code("2001:db8::1", "5555", "123456")
        self.assertFalse(result)

    def test_pair_with_code_invalid_port(self):
        """Test invalid port format."""
        result = self.pairing_manager.pair_with_code("192.168.1.5", "invalid", "123456")
        self.assertFalse(result)


if __name__ == "__main__":
    unittest.main()
