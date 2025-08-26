#!/usr/bin/env python3
"""Quick run script for the memory CLI"""

import sys
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent / "src"))

from memory.cli.commands import cli

if __name__ == "__main__":
    cli()