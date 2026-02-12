import os
import sys
import logging
import importlib
from unittest import mock
import pytest
import tempfile
from pathlib import Path

# Since we need to test the module level code, we need to import it inside the tests or reload it.
# We will import it at the top level to make sure it's available, but reload it in tests.
from aurynk.utils import logger

class TestLogger:
    @pytest.fixture(autouse=True)
    def clean_env(self):
        # Backup environment
        old_env = os.environ.copy()

        # We also need to restore the logger module to its original state after tests
        # or at least ensure we don't leave it in a weird state.

        yield

        # Restore environment
        os.environ.clear()
        os.environ.update(old_env)

        # Reload logger module to restore state to "normal" (though normal depends on env)
        # We can just reload it to clear any mocks we might have set on module level attributes if any.
        importlib.reload(logger)

    def test_logger_respects_xdg_state_home(self, tmp_path):
        xdg_home = tmp_path / "xdg_home"
        os.environ["XDG_STATE_HOME"] = str(xdg_home)

        importlib.reload(logger)

        expected_log_dir = xdg_home / "aurynk"
        assert logger.LOG_DIR == str(expected_log_dir)
        # The module tries to create the directory
        assert expected_log_dir.exists()

    def test_logger_defaults_to_home(self, tmp_path):
        if "XDG_STATE_HOME" in os.environ:
            del os.environ["XDG_STATE_HOME"]

        # Mock expanduser to return a temp path so we don't write to real user home
        fake_home = tmp_path / "home"

        with mock.patch("os.path.expanduser", return_value=str(fake_home)):
            importlib.reload(logger)

            expected_log_dir = fake_home / ".local" / "state" / "aurynk"
            assert logger.LOG_DIR == str(expected_log_dir)
            assert expected_log_dir.exists()

    def test_logger_fallback_on_mkdir_failure(self):
        # Mock Path.mkdir to raise OSError
        with mock.patch("pathlib.Path.mkdir", side_effect=OSError("Permission denied")):
            importlib.reload(logger)

            assert logger.LOG_DIR == tempfile.gettempdir()
            # LOG_FILE should also be updated
            assert logger.LOG_FILE == os.path.join(tempfile.gettempdir(), "aurynk.log")

    def test_get_logger_configuration(self):
        # Ensure clean state
        importlib.reload(logger)

        with mock.patch("logging.getLogger") as mock_get_logger:
            mock_logger_instance = mock.Mock()
            mock_logger_instance.handlers = [] # Initially empty
            mock_get_logger.return_value = mock_logger_instance

            # We also need to verify that handlers are added.
            # The get_logger function creates StreamHandler and RotatingFileHandler.
            # We can mock them to verify they are created with correct parameters.

            with mock.patch("logging.StreamHandler") as mock_stream_handler_cls, \
                 mock.patch("logging.handlers.RotatingFileHandler") as mock_file_handler_cls:

                mock_stream_handler = mock.Mock()
                mock_stream_handler_cls.return_value = mock_stream_handler

                mock_file_handler = mock.Mock()
                mock_file_handler_cls.return_value = mock_file_handler

                log = logger.get_logger("test_logger")

                assert log == mock_logger_instance
                mock_logger_instance.setLevel.assert_called_with(logging.DEBUG)

                # Check that addHandler was called for both handlers
                assert mock_logger_instance.addHandler.call_count == 2
                mock_logger_instance.addHandler.assert_any_call(mock_stream_handler)
                mock_logger_instance.addHandler.assert_any_call(mock_file_handler)

                # Check StreamHandler config
                mock_stream_handler.setLevel.assert_called_with(logging.DEBUG)

                # Check RotatingFileHandler config
                mock_file_handler_cls.assert_called_with(
                    logger.LOG_FILE, maxBytes=1024 * 1024, backupCount=3, encoding="utf-8"
                )
                mock_file_handler.setLevel.assert_called_with(logging.DEBUG)

    def test_get_logger_existing_handlers(self):
        importlib.reload(logger)
        with mock.patch("logging.getLogger") as mock_get_logger:
            mock_logger_instance = mock.Mock()
            mock_logger_instance.handlers = [mock.Mock()] # Already has handlers
            mock_get_logger.return_value = mock_logger_instance

            log = logger.get_logger("test_logger")

            assert log == mock_logger_instance
            # Should not configure if handlers exist
            mock_logger_instance.setLevel.assert_not_called()
            mock_logger_instance.addHandler.assert_not_called()

    def test_file_handler_failure(self, capsys):
        importlib.reload(logger)

        with mock.patch("logging.getLogger") as mock_get_logger, \
             mock.patch("logging.handlers.RotatingFileHandler", side_effect=OSError("Disk full")):

            mock_logger_instance = mock.Mock()
            mock_logger_instance.handlers = []
            mock_get_logger.return_value = mock_logger_instance

            logger.get_logger("test_logger")

            # Check stderr for error message
            captured = capsys.readouterr()
            assert "Failed to setup file logging: Disk full" in captured.err

            # Should still add console handler
            # We can verify that addHandler was called at least once (for console)
            assert mock_logger_instance.addHandler.call_count >= 1
