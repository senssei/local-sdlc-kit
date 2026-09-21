#!/usr/bin/env python3
"""Shim for a git clone: `python3 install.py` re-exports the package installer.

The installer lives at `sdlc_kit.install` so it can ship on PyPI; this top-level file keeps the
git-clone command from `README.md` working without changing it. Not packaged in the wheel.
"""

import sys

from sdlc_kit.install import main

if __name__ == "__main__":
    sys.exit(main())