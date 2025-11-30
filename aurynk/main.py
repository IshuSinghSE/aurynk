import gettext
import os
import sys

# Install gettext globally so _() is available everywhere
# This assumes locale files are in /usr/share/locale or similar, or relative to the app
# For now, we just install it so it doesn't crash.
gettext.install("aurynk", localesdir=os.path.join(os.path.dirname(__file__), "..", "po"))

from aurynk.application import main

if __name__ == "__main__":
    sys.exit(main(sys.argv))
