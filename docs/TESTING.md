# Testing Aurynk

This guide covers testing strategies, running tests, and debugging Aurynk.

## Table of Contents

- [Test Structure](#test-structure)
- [Running Tests](#running-tests)
- [Test Coverage](#test-coverage)
- [Manual Testing](#manual-testing)
- [Testing Specific Components](#testing-specific-components)
- [Debugging](#debugging)
- [Continuous Integration](#continuous-integration)

## Test Structure

Aurynk uses `pytest` for automated testing. Tests are organized in the `tests/` directory:

```
tests/
├── test_adb_manager.py          # ADB operations and device pairing
├── test_audio_stream.py         # Audio streaming functionality
├── test_device_monitor.py       # Device detection and monitoring
├── test_pairing.py              # Wireless pairing logic
├── test_scrcpy_runner.py        # Screen mirroring integration
├── test_scrcpy_runner_stress.py # Stress testing scrcpy
├── test_settings_manager.py     # Settings persistence
├── test_settings_window.py      # Settings UI components
├── test_ssl_context.py          # SSL/TLS configuration
└── test_usb_monitor.py          # USB device detection
```

## Running Tests

### Prerequisites

Install test dependencies:

```bash
# Activate virtual environment
python3 -m venv .venv
source .venv/bin/activate

# Install with dev dependencies
pip install -e ".[dev]"

# Additional test tools (optional)
pip install pytest pytest-cov pytest-xdist
```

### Run All Tests

```bash
# Run all tests
pytest

# Run with verbose output
pytest -v

# Run with detailed output
pytest -vv
```

### Run Specific Tests

```bash
# Run specific test file
pytest tests/test_adb_manager.py

# Run specific test class
pytest tests/test_adb_manager.py::TestADBController

# Run specific test method
pytest tests/test_adb_manager.py::TestADBController::test_generate_code

# Run tests matching pattern
pytest -k "pairing"
pytest -k "test_adb or test_device"
```

### Run Tests in Parallel

```bash
# Install pytest-xdist
pip install pytest-xdist

# Run tests in parallel (auto-detect CPU count)
pytest -n auto

# Run with specific number of workers
pytest -n 4
```

## Test Coverage

### Generate Coverage Report

```bash
# Install coverage tool
pip install pytest-cov

# Run tests with coverage
pytest --cov=aurynk

# Generate HTML coverage report
pytest --cov=aurynk --cov-report=html

# Open coverage report in browser
xdg-open htmlcov/index.html
```

### Coverage Output

```bash
# Show missing lines
pytest --cov=aurynk --cov-report=term-missing

# Generate multiple report formats
pytest --cov=aurynk \
    --cov-report=html \
    --cov-report=term \
    --cov-report=xml
```

### Coverage Configuration

Add to `pyproject.toml`:

```toml
[tool.pytest.ini_options]
testpaths = ["tests"]
python_files = ["test_*.py"]
python_classes = ["Test*"]
python_functions = ["test_*"]

[tool.coverage.run]
source = ["aurynk"]
omit = [
    "*/tests/*",
    "*/__pycache__/*",
    "*/site-packages/*",
]

[tool.coverage.report]
exclude_lines = [
    "pragma: no cover",
    "def __repr__",
    "raise AssertionError",
    "raise NotImplementedError",
    "if __name__ == .__main__.:",
]
```

## Manual Testing

### Testing the Full Application

```bash
# Run from source
python -m aurynk

# Run with debug logging
G_MESSAGES_DEBUG=all python -m aurynk

# Run with Python debugging
python -m pdb -m aurynk
```

### Testing Specific Scenarios

#### Wireless Pairing

1. **Start Aurynk**
   ```bash
   python -m aurynk
   ```

2. **Enable Wireless Debugging on Android**
   - Settings → Developer Options → Wireless Debugging
   - Note the port number (usually 5555)

3. **Test QR Pairing**
   - Click "Add Device" in Aurynk
   - On Android: tap "Pair device with QR code"
   - Scan the QR code shown in Aurynk
   - Verify connection is established

4. **Test Manual Pairing**
   - On Android: tap "Pair device with pairing code"
   - Enter IP address and pairing port in Aurynk
   - Enter the 6-digit code from Android
   - Verify connection is established

#### USB Device Detection

```bash
# Test USB monitoring
adb devices

# Connect device via USB
# Verify Aurynk detects the device

# Disconnect device
# Verify Aurynk updates device list
```

#### Screen Mirroring

```bash
# Ensure scrcpy is installed
which scrcpy

# Test mirroring through Aurynk
# Click the monitor icon next to a device
# Verify screen appears and is responsive
```

#### Screenshot Capture

```bash
# Test screenshot functionality
# Click camera icon next to a device
# Verify screenshot is saved to ~/Pictures/Aurynk/
ls ~/Pictures/Aurynk/
```

### Testing with Different Device States

1. **Connected Device**
   - Verify all device info displays correctly
   - Test all available actions

2. **Disconnected Device**
   - Disconnect WiFi or disable debugging
   - Verify Aurynk shows offline status
   - Test reconnection

3. **Multiple Devices**
   - Connect 2+ devices
   - Verify all devices appear in list
   - Test actions on each device independently

4. **Low Battery Device**
   - Let device battery drop below 20%
   - Verify battery status displays correctly

## Testing Specific Components

### ADB Manager

```bash
pytest tests/test_adb_manager.py -v
```

**What it tests:**
- Device pairing (QR and manual)
- ADB command execution
- Device connection/disconnection
- Error handling

### Device Monitor

```bash
pytest tests/test_device_monitor.py -v
```

**What it tests:**
- Device discovery
- Device state changes
- Connection monitoring
- Event callbacks

### Settings Manager

```bash
pytest tests/test_settings_manager.py -v
```

**What it tests:**
- Settings persistence
- Default values
- Settings validation
- Configuration updates

### USB Monitor

```bash
pytest tests/test_usb_monitor.py -v
```

**What it tests:**
- USB device detection
- Device authorization
- udev integration
- Permission handling

### Scrcpy Integration

```bash
pytest tests/test_scrcpy_runner.py -v
```

**What it tests:**
- Scrcpy process management
- Screen mirroring initialization
- Error handling
- Process cleanup

**Stress testing:**
```bash
pytest tests/test_scrcpy_runner_stress.py -v
```

## Debugging

### Enable Debug Logging

```bash
# Set environment variable
export AURYNK_DEBUG=1
python -m aurynk

# Or use GLib debug
G_MESSAGES_DEBUG=all python -m aurynk
```

### Logging Configuration

Aurynk uses Python's logging module. Adjust log levels in code:

```python
from aurynk.utils.logger import get_logger

logger = get_logger("ComponentName")
logger.setLevel(logging.DEBUG)
```

### Debug Specific Components

```bash
# Debug ADB operations
G_MESSAGES_DEBUG=ADB python -m aurynk

# Debug device monitoring
G_MESSAGES_DEBUG=DeviceMonitor python -m aurynk

# Debug all components
G_MESSAGES_DEBUG=all python -m aurynk
```

### Using Python Debugger

```bash
# Run with pdb
python -m pdb -m aurynk

# Set breakpoint in code
import pdb; pdb.set_trace()

# Or use breakpoint() (Python 3.12+)
breakpoint()
```

### Using VS Code Debugger

Create `.vscode/launch.json`:

```json
{
  "version": "0.2.0",
  "configurations": [
    {
      "name": "Aurynk",
      "type": "debugpy",
      "request": "launch",
      "module": "aurynk",
      "console": "integratedTerminal",
      "env": {
        "AURYNK_DEBUG": "1",
        "G_MESSAGES_DEBUG": "all"
      }
    },
    {
      "name": "Aurynk Tests",
      "type": "debugpy",
      "request": "launch",
      "module": "pytest",
      "args": ["-v"],
      "console": "integratedTerminal"
    }
  ]
}
```

### Debugging Flatpak Build

```bash
# Enter Flatpak build environment
flatpak-builder --run build-dir \
    flatpak/io.github.IshuSinghSE.aurynk.yml \
    /bin/bash

# Inside the environment, test commands
python3 -m aurynk
```

### Common Issues

#### Tests Hang

```bash
# Run with timeout
pytest --timeout=30

# Or kill hanging process
pkill -f pytest
```

#### GTK Warnings

```bash
# Run in offscreen mode (for CI/headless)
xvfb-run pytest

# Or ignore GTK warnings
pytest -W ignore::DeprecationWarning
```

#### Mock Object Issues

```python
# Reset mocks between tests
from unittest.mock import MagicMock, patch

@patch('aurynk.core.adb_manager.subprocess.run')
def test_something(mock_run):
    mock_run.reset_mock()  # Reset before test
    # ... test code ...
```

## Continuous Integration

### GitHub Actions

Tests run automatically on:
- Push to main/develop branches
- Pull requests
- Release tags

### CI Configuration

See `.github/workflows/` for CI pipelines:

```yaml
# Example: Run tests on push
name: Tests

on: [push, pull_request]

jobs:
  test:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3
      - name: Set up Python
        uses: actions/setup-python@v4
        with:
          python-version: '3.11'
      - name: Install dependencies
        run: |
          pip install -e ".[dev]"
          pip install pytest pytest-cov
      - name: Run tests
        run: pytest --cov=aurynk
```

### Pre-commit Hooks

Set up pre-commit hooks to run tests before commit:

```bash
# Install pre-commit
pip install pre-commit

# Create .pre-commit-config.yaml
cat > .pre-commit-config.yaml << EOF
repos:
  - repo: local
    hooks:
      - id: pytest
        name: pytest
        entry: pytest
        language: system
        pass_filenames: false
        always_run: true
      - id: ruff
        name: ruff
        entry: ruff check
        language: system
        types: [python]
EOF

# Install hooks
pre-commit install
```

## Testing Checklist

Before submitting a PR, ensure:

- [ ] All tests pass: `pytest`
- [ ] No linting errors: `ruff check .`
- [ ] Code formatted: `ruff format .`
- [ ] New tests added for new features
- [ ] Documentation updated
- [ ] Manual testing performed
- [ ] No debug print statements left
- [ ] Git history is clean

## Performance Testing

### Benchmark Tests

```bash
# Time critical operations
pytest tests/ --durations=10

# Profile tests
python -m cProfile -o profile.stats -m pytest
python -m pstats profile.stats
```

### Memory Profiling

```bash
# Install memory profiler
pip install memory-profiler

# Profile memory usage
python -m memory_profiler aurynk/application.py
```

### Load Testing

Test with multiple devices:

```bash
# Simulate multiple devices
pytest tests/test_scrcpy_runner_stress.py -v
```

## Reporting Issues

When reporting test failures, include:

1. **Test command used**
2. **Full error output**
3. **System information**
   ```bash
   python --version
   uname -a
   ```
4. **Installed package versions**
   ```bash
   pip list
   ```
5. **Steps to reproduce**

---

**Need Help?**
- 📖 [Documentation](https://ishusinghse.github.io/aurynk/)
- 💬 [Discussions](https://github.com/IshuSinghSE/aurynk/discussions)
- 🐛 [Bug Reports](https://github.com/IshuSinghSE/aurynk/issues)
