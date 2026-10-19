"""Spell checking with codespell."""

from __future__ import annotations

import os
import pathlib
from typing import Any

import nox

from src.config import error_as_warning
from src.runner import report, require_config
from src.workspace import in_container, resolve_targets, workspace_from

_SKIP = ",".join(
    (
        ".git",
        "repos",
        ".nox*",
        ".venv*",
        "__pycache__",
        ".pytest_cache",
        "*.svg",
    )
)
_IGNORE_REGEX = r"\$\{[^}]+\}|##vso\[[^\]]+\]|::(error|warning|notice)::"


def _local_ignore_files(root: pathlib.Path) -> list[pathlib.Path]:
    """Return project codespell ignore lists in the workspace root."""
    return sorted(path for path in root.glob("*codespell*") if path.is_file())


def run_codespell(session: Any) -> None:
    """Spell-check text files with codespell."""
    if not in_container():
        session.install("codespell==2.4.1")
    ignore_words = require_config(session, "codespell", "codespell", "ignore-words.txt")
    root = workspace_from(session.invoked_from)
    with session.chdir(root):
        skip, files = resolve_targets(list(session.posargs), "codespell.files", ["."])
        if skip:
            session.skip("No files to check")
        extra = os.environ.get("CODESPELL_IGNORE_WORDS")
        ignore_files = [str(ignore_words)]
        if extra:
            ignore_files.append(
                str((root / extra).resolve() if not os.path.isabs(extra) else extra)
            )
        ignore_files.extend(str(path.resolve()) for path in _local_ignore_files(root))
        command = [
            "codespell",
            "--ignore-words",
            ",".join(ignore_files),
            "--ignore-regex",
            _IGNORE_REGEX,
            "--uri-ignore-words-list",
            "*",
            "--skip",
            _SKIP,
            *files,
        ]
        try:
            session.run(*command, external=in_container())
        except nox.command.CommandFailed as exc:
            # Without a project word list, spelling stays a warning.
            warning = (
                error_as_warning("codespell", "error_as_warning")
                if _local_ignore_files(root)
                else True
            )
            report(session, "Codespell check failed", warning, str(exc))
