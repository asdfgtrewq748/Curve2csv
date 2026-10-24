"""PyInstaller entry. A console build so ``--headless-smoke`` can print."""

from __future__ import annotations

import sys

from curve2csv.__main__ import main

if __name__ == "__main__":
    sys.exit(main())
