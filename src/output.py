"""Process output for checks and command-line entry points.

GitHub Actions and Azure Pipelines parse a few exact stdout lines
(``::error::``, ``::warning::``, ``##vso``, ``##[group]``). Those lines are
written with no logger prefix. Every other message goes through the ``gbv``
logger on stderr.
"""

from __future__ import annotations

import logging
import sys

_LOGGER = logging.getLogger("gbv")


def _configure() -> None:
    """Attach one stderr handler to the package logger."""
    if _LOGGER.handlers:
        return
    handler = logging.StreamHandler(sys.stderr)
    handler.setFormatter(logging.Formatter("%(levelname)s %(name)s: %(message)s"))
    _LOGGER.addHandler(handler)
    _LOGGER.setLevel(logging.INFO)
    _LOGGER.propagate = False


def ci(line: str) -> None:
    """Write one host logging command to stdout."""
    sys.stdout.write(f"{line}\n")
    sys.stdout.flush()


def result(value: object) -> None:
    """Write a command result to stdout with no log prefix."""
    sys.stdout.write(f"{value}\n")
    sys.stdout.flush()


def info(message: str) -> None:
    """Record a progress message."""
    _configure()
    _LOGGER.info(message)


def error(message: str) -> None:
    """Record an error on stderr."""
    _configure()
    _LOGGER.error(message)
