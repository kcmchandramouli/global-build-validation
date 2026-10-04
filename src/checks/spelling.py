"""CSpell analysis."""

from __future__ import annotations

import os
import pathlib
from typing import Any

import nox
import yaml

from src.runner import node_command, report
from src.workspace import bundled_config, resolve_targets, workspace_from


def _local_configs(root: pathlib.Path) -> list[pathlib.Path]:
    """Return project CSpell files in the workspace root."""
    return sorted(path for path in root.glob("*cspell.*") if path.is_file())


def _import_path(root: pathlib.Path, value: str) -> str:
    """Return an absolute path so CSpell can import it from /tmp."""
    path = pathlib.Path(value)
    if not path.is_absolute():
        path = root / path
    return str(path.resolve())


def _write_config(root: pathlib.Path, destination: pathlib.Path) -> None:
    """Merge the bundled dictionary with project and pipeline config.

    Imports are absolute. The generated file lives in /tmp, and CSpell
    resolves relative imports from that directory.
    """
    default_config = bundled_config("cspell", "cspell.json")
    if default_config is None:
        raise FileNotFoundError("Missing CSpell configuration file")
    imports = [str(default_config.resolve())]
    extra = os.environ.get("CSPELL_CONFIG_FILE")
    if extra:
        imports.append(_import_path(root, extra))
    pipeline_json = os.environ.get("CSPELL_CONFIG_CONTENT_JSON")
    if pipeline_json:
        pipeline_path = pathlib.Path("/tmp/cspell.pipeline.json")
        pipeline_path.write_text(pipeline_json, encoding="utf-8")
        imports.append(str(pipeline_path))
    imports.extend(str(path.resolve()) for path in _local_configs(root))
    destination.write_text(
        yaml.safe_dump({"import": imports}, sort_keys=False),
        encoding="utf-8",
    )


def run_cspell(session: Any) -> None:
    """Spell-check text files with CSpell."""
    root = workspace_from(session.invoked_from)
    destination = pathlib.Path("/tmp/cspell.yml")
    try:
        _write_config(root, destination)
    except FileNotFoundError as exc:
        session.error(str(exc))
    with session.chdir(root):
        session.log(
            "CSpell configuration file is:\n" + destination.read_text(encoding="utf-8")
        )
        skip, patterns = resolve_targets(list(session.posargs), "cspell.files", ["**"])
        if skip:
            session.skip("No files to check")
        command = [
            *node_command(session, "cspell@6", "cspell"),
            "lint",
            "--show-suggestions",
            "--color",
            "--no-must-find-files",
            "--config",
            str(destination),
            *patterns,
        ]
        try:
            session.run(*command, external=True)
        except nox.command.CommandFailed as exc:
            # Without a project dictionary, CSpell stays a warning.
            if _local_configs(root):
                warning = os.getenv("ERROR_AS_WARNING", "false").casefold() == "true"
            else:
                warning = True
            report(session, "CSpell check failed", warning, str(exc))
