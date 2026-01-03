"""Entry point for running aurynk as a module: python -m aurynk or as a script"""

import gettext
import os
import sys

# Install gettext globally so _() is available everywhere
# This assumes locale files are in /usr/share/locale or similar, or relative to the app
gettext.install("aurynk", localedir=os.path.join(os.path.dirname(__file__), "..", "po"))

from aurynk.application import main
from aurynk.utils.logger import get_logger

logger = get_logger("Main")

if __name__ == "__main__":
    try:
        sys.exit(main(sys.argv))
    except KeyboardInterrupt:
        # Graceful shutdown on Ctrl-C from terminal
        logger.info("Interrupted by user (KeyboardInterrupt). Exiting.")
        # Best-effort cleanup of sockets
        try:
            app_sock = "/tmp/aurynk_app.sock"
            tray_sock = "/tmp/aurynk_tray.sock"
            if os.path.exists(app_sock):
                os.unlink(app_sock)
            if os.path.exists(tray_sock):
                os.unlink(tray_sock)
        except Exception:
            pass
        sys.exit(0)
