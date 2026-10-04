"""Allow `python -m src` to start the container entrypoint."""

from __future__ import annotations

import sys

from src.entrypoint import main

if __name__ == "__main__":
    sys.exit(main())
