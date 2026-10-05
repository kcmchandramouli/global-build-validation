"""Markdown lint, link checks, and Markdown/YAML formatting."""

from __future__ import annotations

import base64
import json
import os
import pathlib
from typing import Any

from src.runner import require_config, wrap
from src.workspace import (
    bundled_config,
    first_file,
    in_container,
    read_modified_files,
    resolve_targets,
    walk_files,
    workspace_from,
)

_PACKAGE_ROOT = pathlib.Path(__file__).resolve().parents[2]
_PYMARKDOWN_EXCLUDES = (
    ".nox/**",
    ".venv/**",
    "repos/**",
    "**/__pycache__/**",
    ".git/**",
)
_FORMAT_EXCLUDES = (".nox/**", ".venv/**", "repos/**", ".git/**")


def run_markdownlint(session: Any) -> None:
    """Lint Markdown with PyMarkdown. Line length (MD013) is disabled."""
    if not in_container():
        session.install("pymarkdownlnt==0.9.32")
    root = workspace_from(session.invoked_from)
    with session.chdir(root):
        skip, files = resolve_targets(
            list(session.posargs), "markdownlint.files", ["."]
        )
        if skip:
            session.skip("No files to check")
        command = ["pymarkdown", "-d", "md013", "scan", "-r"]
        for pattern in _PYMARKDOWN_EXCLUDES:
            command.extend(["-e", pattern])
        with wrap(session, "Markdownlint failed", "markdownlint", "error_as_warning"):
            session.run(*command, *files, external=in_container())


def prepare_link_config(config_path: pathlib.Path, out_path: pathlib.Path) -> None:
    """Write link-check config, including an optional auth header."""
    try:
        with config_path.open(encoding="utf-8") as handle:
            config = json.load(handle)
    except json.JSONDecodeError as exc:
        raise ValueError(f"Invalid markdown-link-check configuration: {exc}") from exc
    if not isinstance(config, dict):
        raise ValueError("markdown-link-check configuration must be a JSON object")
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
            raise ValueError(
                "markdown-link-check configuration is missing httpHeaders"
            ) from exc
    with out_path.open("w", encoding="utf-8") as handle:
        json.dump(config, handle)


def run_markdown_link_check(session: Any) -> None:
    """Check HTTP(S) links in Markdown files."""
    if not in_container():
        session.install("requests==2.32.3")
    candidates = [pathlib.Path("/etc/markdown-link-check/config.json")]
    bundled = bundled_config("markdown-link-check", "markdown-link-check.json")
    if bundled is not None:
        candidates.append(bundled)
    config = first_file(*candidates)
    if config is None or not config.is_file():
        session.error("Missing markdown-link-check configuration")
        return
    root = workspace_from(session.invoked_from)
    out_path = pathlib.Path("/tmp/markdown-link-check.json")
    with session.chdir(root):
        try:
            prepare_link_config(config, out_path)
        except ValueError as exc:
            session.error(str(exc))
            return
        files = list(session.posargs) or walk_files(root, ".md")
        if not files:
            session.log("No Markdown files to check.")
            return
        session.env["PYTHONPATH"] = str(_PACKAGE_ROOT)
        with wrap(
            session,
            "Markdown link check failed",
            "markdown-link-check",
            "error_as_warning",
        ):
            session.run(
                "python",
                "-m",
                "src.checks.links",
                str(out_path),
                *files,
                external=in_container(),
            )


def _partition(files: list[str]) -> tuple[list[str], list[str], list[str]]:
    """Split paths into Markdown, YAML, and everything else."""
    markdown: list[str] = []
    yaml_files: list[str] = []
    skipped: list[str] = []
    for path in files:
        lowered = path.casefold()
        if path == "." or pathlib.Path(path).is_dir():
            markdown.append(path)
            yaml_files.append(path)
        elif lowered.endswith(".md"):
            markdown.append(path)
        elif lowered.endswith((".yml", ".yaml")):
            yaml_files.append(path)
        else:
            skipped.append(path)
    return markdown, yaml_files, skipped


def _extend_excludes(command: list[str], flag: str) -> None:
    """Append repeated exclude flags."""
    for pattern in _FORMAT_EXCLUDES:
        command.extend([flag, pattern])


def _markdown_files(root: pathlib.Path, paths: list[str]) -> list[str]:
    """Expand directories to Markdown files, skipping tool and VCS dirs."""
    found: list[str] = []
    seen: set[str] = set()
    for path in paths:
        if path == "." or pathlib.Path(path).is_dir():
            base = root if path == "." else pathlib.Path(path)
            matches = [
                str((base / match).resolve().relative_to(root.resolve()))
                for match in walk_files(base, ".md")
            ]
        else:
            matches = [path]
        for match in matches:
            if match not in seen:
                seen.add(match)
                found.append(match)
    return found


def run_format(session: Any) -> None:
    """Check Markdown with mdformat and YAML with yamlfix.

    TOML is not checked. No Python formatter covers it the way Prettier did.
    """
    if not in_container():
        session.install("mdformat==0.7.22", "yamlfix==1.17.0")
    yamlfix_config = require_config(session, "yamlfix", "yamlfix", "pyproject.toml")
    root = workspace_from(session.invoked_from)
    with session.chdir(root):
        listed = read_modified_files("format.files")
        if session.posargs:
            files = list(session.posargs)
        elif listed is None:
            files = ["."]
        elif not listed:
            session.skip("No files to check")
            return
        else:
            files = listed
        markdown, yaml_files, skipped = _partition(files)
        toml_files = [path for path in skipped if path.casefold().endswith(".toml")]
        if toml_files:
            session.log("TOML formatting is not checked: " + ", ".join(toml_files))
        markdown = _markdown_files(root, markdown)
        if markdown:
            command = [
                "mdformat",
                "--check",
                "--wrap",
                "keep",
                "--end-of-line",
                "lf",
            ]
            with wrap(
                session,
                "Markdown format failed",
                "markdown-format",
                "error_as_warning",
            ):
                session.run(*command, *markdown, external=in_container())
        if yaml_files:
            command = ["yamlfix", "--check", "-c", str(yamlfix_config)]
            _extend_excludes(command, "-e")
            with wrap(session, "YAML format failed", "yaml-format", "error_as_warning"):
                session.run(*command, *yaml_files, external=in_container())
