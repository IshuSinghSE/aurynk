#!/usr/bin/env python3
"""Entry point for running mirage as a module: python -m mirage"""

import sys
from mirage.app import main

if __name__ == "__main__":
    sys.exit(main(sys.argv))
