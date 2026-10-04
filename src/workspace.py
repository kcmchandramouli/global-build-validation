"""Paths, CI file lists, and bundled checker configuration."""

from __future__ import annotations

import os
import pathlib
from typing import Optional

PRUNE_DIR_NAMES = {".git", "repos", "__pycache__", ".pytest_cache"}
SHARE = pathlib.Path(__file__).resolve().parent / "share"


def in_container() -> bool:
    """Return True when the process was started by the container entrypoint."""
    return bool(os.environ.get("DOCKER_ENTRYPOINT"))


def workspace_from(invoked_from: str) -> pathlib.Path:
    """Return the directory nox was started from."""
    return pathlib.Path(invoked_from).resolve()


def first_file(*candidates: pathlib.Path) -> Optional[pathlib.Path]:
    """Return the first path that exists."""
    for path in candidates:
        if path.is_file():
            return path
    return None


def bundled_config(*relative: str) -> Optional[pathlib.Path]:
    """Find a checker config shipped with this package."""
    return first_file(
        pathlib.Path("/etc").joinpath(*relative),
        SHARE.joinpath(*relative),
    )


def read_modified_files(
    list_name: str, directory: Optional[pathlib.Path] = None
) -> Optional[list[str]]:
    """Return paths from a CI file list.

    None means the list file is absent. An empty list means the CI list
    exists and no files changed.
    """
    folder = directory if directory is not None else pathlib.Path("/tmp")
    path = folder / list_name
    if not path.is_file():
        return None
    return [
        line for line in path.read_text(encoding="utf-8").splitlines() if line != ""
    ]


def resolve_targets(
    posargs: list[str],
    list_name: str,
    default: list[str],
    directory: Optional[pathlib.Path] = None,
) -> tuple[bool, list[str]]:
    """Return (skip, files) for a check.

    Positional args win. A present-but-empty CI list skips the check.
    """
    if posargs:
        return False, list(posargs)
    listed = read_modified_files(list_name, directory)
    if listed is None:
        return False, default
    if not listed:
        return True, []
    return False, listed


def walk_files(root: pathlib.Path, suffix: str) -> list[str]:
    """Return files ending with suffix, skipping tool and VCS directories."""
    matches: list[str] = []
    for dirpath, dirnames, filenames in os.walk(root):
        dirnames[:] = [
            name
            for name in dirnames
            if name not in PRUNE_DIR_NAMES
            and not name.startswith(".nox")
            and not name.startswith(".venv")
        ]
        for filename in filenames:
            if filename.endswith(suffix):
                full = pathlib.Path(dirpath, filename)
                matches.append(str(full.relative_to(root)))
    return matches
