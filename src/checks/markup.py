"""Markdown, link, and Prettier analysis."""

from __future__ import annotations

import base64
import json
import os
import pathlib
from typing import Any

import nox

from src.runner import CheckFailed, node_command, require_config, wrap
from src.workspace import (
    bundled_config,
    first_file,
    read_modified_files,
    resolve_targets,
    walk_files,
    workspace_from,
)


def run_markdownlint(session: Any) -> None:
    """Lint Markdown with markdownlint-cli2."""
    config = require_config(
        session,
        "markdownlint",
        "markdownlint-cli2",
        ".markdownlint-cli2.yaml",
    )
    root = workspace_from(session.invoked_from)
    with session.chdir(root):
        skip, files = resolve_targets(
            list(session.posargs), "markdownlint-cli2.files", ["**/*.md"]
        )
        if skip:
            session.skip("No files to check")
        command = node_command(session, "markdownlint-cli2", "markdownlint-cli2-config")
        with wrap(session, "Markdownlint failed", "markdownlint", "error_as_warning"):
            session.run(*command, str(config), *files, external=True)


def prepare_link_config(config_path: pathlib.Path, out_path: pathlib.Path) -> None:
    """Write markdown-link-check config, including an optional auth header."""
    try:
        with config_path.open(encoding="utf-8") as handle:
            config = json.load(handle)
    except json.JSONDecodeError as exc:
        raise CheckFailed(f"Invalid markdown-link-check configuration: {exc}") from exc
    if not isinstance(config, dict):
        raise CheckFailed("markdown-link-check configuration must be a JSON object")
    token = None
    pat = os.getenv("AUTHORIZATION_PAT")
    if pat is not None:
        encoded = base64.standard_b64encode(f":{pat}".encode()).decode("utf-8")
        token = "Basic " + encoded
    else:
        token = os.getenv("AUTHORIZATION_TOKEN")
    if token is None:
        config.pop("httpHeaders", None)
    else:
        try:
            config["httpHeaders"][0]["headers"]["Authorization"] = token
            config["aliveStatusCodes"] = [
                code for code in config["aliveStatusCodes"] if code != 203
            ]
        except (KeyError, IndexError, TypeError) as exc:
            raise CheckFailed(
                "markdown-link-check configuration is missing httpHeaders"
            ) from exc
    with out_path.open("w", encoding="utf-8") as handle:
        json.dump(config, handle)


def run_markdown_link_check(session: Any) -> None:
    """Check links in Markdown files."""
    candidates = [pathlib.Path("/etc/markdown-link-check/config.json")]
    bundled = bundled_config("markdown-link-check", "markdown-link-check.json")
    if bundled is not None:
        candidates.append(bundled)
    config = first_file(*candidates)
    if config is None or not config.is_file():
        session.error("Missing markdown-link-check configuration")
    root = workspace_from(session.invoked_from)
    out_path = pathlib.Path("/tmp/markdown-link-check.json")
    with session.chdir(root):
        prepare_link_config(config, out_path)
        files = list(session.posargs) or walk_files(root, ".md")
        if not files:
            session.log("No Markdown files to check.")
            return
        command = node_command(session, "markdown-link-check@3", "markdown-link-check")
        failed = False
        for path in files:
            try:
                session.run(
                    *command,
                    "--verbose",
                    "--config",
                    str(out_path),
                    path,
                    external=True,
                )
            except nox.command.CommandFailed:
                failed = True
        if failed:
            with wrap(
                session,
                "Markdown link check failed",
                "markdown-link-check",
                "error_as_warning",
            ):
                raise CheckFailed("Markdown link check failed")


def run_prettier(session: Any) -> None:
    """Check Markdown, YAML, and TOML formatting with Prettier."""
    config = require_config(session, "prettier", "prettier-check", ".prettierrc")
    root = workspace_from(session.invoked_from)
    with session.chdir(root):
        listed = read_modified_files("prettier-check.files")
        command = [
            *node_command(session, "prettier@3", "prettier"),
            "--no-editorconfig",
            "--config",
            str(config),
            "--check",
        ]
        if session.posargs:
            files = list(session.posargs)
        elif listed is None:
            command.append("--no-error-on-unmatched-pattern")
            files = ["**/*.md", "**/*.yaml", "**/*.yml", "**/*.toml"]
        elif not listed:
            session.skip("No files to check")
            return
        else:
            files = listed
        with wrap(session, "Prettier check failed", "prettier", "error_as_warning"):
            session.run(*command, *files, external=True)
