import unittest
from unittest.mock import patch

from aurynk.core.audio_stream import AudioStreamManager


class TestAudioStreamManager(unittest.TestCase):
    def setUp(self):
        self.manager = AudioStreamManager()

    @patch("aurynk.core.audio_stream.subprocess.check_output")
    def test_start_stream(self, mock_check_output):
        # Setup mocks to return module IDs
        mock_check_output.side_effect = [b"123\n", b"124\n"]

        self.manager.start_stream(12345)

        # Verify calls
        self.assertEqual(mock_check_output.call_count, 2)

        # Check first call (null-sink)
        args1, _ = mock_check_output.call_args_list[0]
        cmd1 = args1[0]
        self.assertEqual(cmd1[:3], ["pactl", "load-module", "module-null-sink"])
        self.assertIn("sink_name=aurynk_audio_12345", cmd1)

        # Check second call (tcp)
        args2, _ = mock_check_output.call_args_list[1]
        cmd2 = args2[0]
        self.assertEqual(cmd2[:3], ["pactl", "load-module", "module-simple-protocol-tcp"])
        self.assertIn("port=12345", cmd2)
        self.assertIn("sink=aurynk_audio_12345", cmd2)

        # Verify IDs stored
        self.assertEqual(self.manager._module_ids, ["123", "124"])

    @patch("aurynk.core.audio_stream.subprocess.run")
    @patch("aurynk.core.audio_stream.subprocess.check_output")
    def test_stop_stream(self, mock_check_output, mock_run):
        # Setup state by running start_stream first
        mock_check_output.side_effect = [b"123\n", b"124\n"]
        self.manager.start_stream(12345)

        # Run stop
        self.manager.stop_stream()

        # Verify unload calls
        self.assertEqual(mock_run.call_count, 2)

        # Should unload in reverse order: 124 then 123
        call1 = mock_run.call_args_list[0]
        call2 = mock_run.call_args_list[1]

        self.assertEqual(call1[0][0], ["pactl", "unload-module", "124"])
        self.assertEqual(call2[0][0], ["pactl", "unload-module", "123"])

        # Verify list is empty
        self.assertEqual(self.manager._module_ids, [])

    @patch("aurynk.core.audio_stream.subprocess.check_output")
    def test_start_stream_failure(self, mock_check_output):
        # Simulate failure on first command
        import subprocess

        mock_check_output.side_effect = subprocess.CalledProcessError(1, "cmd")

        with self.assertRaises(subprocess.CalledProcessError):
            self.manager.start_stream(12345)

        # Should not have stored any IDs if first failed
        self.assertEqual(self.manager._module_ids, [])
