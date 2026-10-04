"""Shared nox command helpers for analysis sessions."""

from __future__ import annotations

import contextlib
import shutil
from typing import Any, Generator

import nox

from src.config import error_as_warning
from src.workspace import bundled_config


class CheckFailed(Exception):
    """A check failed before the underlying tool exited."""


def _emit(line: str) -> None:
    """Print a CI command on its own line, without a nox prefix."""
    print(line, flush=True)  # noqa: T201


def report(session: Any, message: str, warning: bool, detail: str) -> None:
    """Emit GitHub Actions and Azure Pipelines annotations, then stop or warn.

    Annotations are written to stdout. nox prefixes its own log lines, and
    appending them to ``session.error`` lets the session duration land on the
    Azure logging command.
    """
    if warning:
        summary = f"{message} (warn only)"
        _emit(f"::warning::{summary}")
        _emit(f"##vso[task.logissue type=warning]{summary}")
        _emit("##vso[task.complete result=SucceededWithIssues]")
        session.warn(f"{summary}: {detail}")
        return
    _emit(f"::error::{message}")
    _emit(f"##vso[task.logissue type=error]{message}")
    _emit("##vso[task.complete result=Failed]")
    session.error(f"{message}: {detail}")


@contextlib.contextmanager
def wrap(session: Any, message: str, *config_path: str) -> Generator[None, None, None]:
    """Turn a failed command into a warning when configured."""
    try:
        yield
    except (nox.command.CommandFailed, CheckFailed) as exc:
        report(session, message, error_as_warning(*config_path), str(exc))


def node_command(session: Any, package: str, binary: str) -> list[str]:
    """Return a global binary, or an npx command that fetches it."""
    found = shutil.which(binary)
    if found:
        return [found]
    if shutil.which("npx") is None:
        session.error(
            f"{binary} is not on PATH. Install Node.js 18+ and rerun "
            f"nox -s {session.name}"
        )
    return ["npx", "--yes", "--package", package, binary]


def require_config(session: Any, label: str, *relative: str) -> Any:
    """Return a bundled config path or fail the session."""
    path = bundled_config(*relative)
    if path is None:
        session.error(f"Missing {label} configuration file")
    return path
