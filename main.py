#!/usr/bin/env python3
"""Iron Lance Mechbay Operations — entry point."""

import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "src"))

from mech_quartermaster.game import run

if __name__ == "__main__":
    try:
        run()
    except Exception:
        import traceback
        traceback.print_exc()
        input("\nPress Enter to close...")
