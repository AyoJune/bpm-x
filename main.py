#!/usr/bin/env python
"""Convenience launcher for BPM-X.

Usage:
    python main.py                 # launch GUI
    python main.py <command> ...   # run CLI command
"""

import sys
from interface.cli import run_cli
from interface.gui import run_gui


def main() -> int:
    """Launch GUI by default, or CLI when arguments are provided."""
    if len(sys.argv) == 1:
        run_gui()
        return 0
    return run_cli()


if __name__ == "__main__":
    sys.exit(main())
