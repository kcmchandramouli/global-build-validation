"""YAML analysis."""

from __future__ import annotations

from typing import Any

from src.runner import require_config, wrap
from src.workspace import in_container, resolve_targets, workspace_from


def run_yamllint(session: Any) -> None:
    """Lint YAML files with yamllint."""
    if not in_container():
        session.install("yamllint==1.35.1")
    config = require_config(session, "yamllint", "yamllint", ".yamllint.yaml")
    root = workspace_from(session.invoked_from)
    with session.chdir(root):
        skip, files = resolve_targets(list(session.posargs), "yamllint.files", ["."])
        if skip:
            session.skip("No files to check")
        with wrap(session, "Yamllint failed", "yamllint", "error_as_warning"):
            session.run(
                "yamllint",
                "-c",
                str(config),
                *files,
                external=in_container(),
            )
