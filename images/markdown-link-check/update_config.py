#!/usr/bin/env python3
"""Inject an optional authorization header into markdown-link-check config."""

from __future__ import annotations

import base64
import json
import os
import pathlib
import sys


def main() -> int:
    """Write /tmp/markdown-link-check.json."""
    config_path = pathlib.Path("/etc/markdown-link-check/config.json")
    with config_path.open(encoding="utf-8") as handle:
        config = json.load(handle)

    token = None
    pat = os.getenv("AUTHORIZATION_PAT")
    if pat is not None:
        token = "Basic " + base64.standard_b64encode(f":{pat}".encode()).decode("utf-8")
    else:
        token = os.getenv("AUTHORIZATION_TOKEN")

    if token is None:
        config.pop("httpHeaders", None)
    else:
        config["httpHeaders"][0]["headers"]["Authorization"] = token
        config["aliveStatusCodes"] = [code for code in config["aliveStatusCodes"] if code != 203]

    out_path = pathlib.Path("/tmp/markdown-link-check.json")
    with out_path.open("w", encoding="utf-8") as handle:
        json.dump(config, handle)
    return 0


if __name__ == "__main__":
    sys.exit(main())
