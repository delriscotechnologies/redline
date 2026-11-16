#!/usr/bin/env python3
"""Zero-install launcher: python redline.py <command>."""

import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent / "src"))

from redline.cli import main  # noqa: E402

if __name__ == "__main__":
    raise SystemExit(main())
