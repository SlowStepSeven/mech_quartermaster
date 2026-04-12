#!/usr/bin/env python3
"""Iron Lance Mechbay Operations — entry point."""

import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "src"))

from mech_quartermaster.app import main

if __name__ == "__main__":
    main()
