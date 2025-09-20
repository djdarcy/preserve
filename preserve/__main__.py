#!/usr/bin/env python3
"""
Entry point for running preserve as a module: python -m preserve
"""

import sys
from .preserve import main

if __name__ == "__main__":
    sys.exit(main())