#!/usr/bin/env python3
"""Entry point for running aurynk as a module: python -m aurynk"""

import sys
from aurynk.app import main

if __name__ == "__main__":
    sys.exit(main(sys.argv))
