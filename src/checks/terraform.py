"""Terraform formatting and Checkov analysis."""

from __future__ import annotations

import shutil
import subprocess
from typing import Any

from src.runner import CheckFailed, wrap
from src.workspace import in_container, resolve_targets, walk_files, workspace_from


def run_terraform_format(session: Any) -> None:
    """Check terraform fmt."""
    if shutil.which("terraform") is None:
        session.error(
            "terraform is not on PATH. Install Terraform, then rerun "
            "nox -s terraform-format"
        )
    root = workspace_from(session.invoked_from)
    with session.chdir(root):
        skip, files = resolve_targets(
            list(session.posargs),
            "terraform-format.files",
            walk_files(root, ".tf"),
        )
        if skip:
            session.skip("No files to check")
        if not files:
            session.log("No Terraform files found.")
            return
        unformatted = 0
        for path in files:
            session.log(f"Checking '{path}'...")
            result = subprocess.run(
                ["terraform", "fmt", "-check", "-diff", path],
                check=False,
            )
            if result.returncode != 0:
                unformatted += 1
        if unformatted:
            with wrap(
                session,
                "Terraform format failed",
                "terraform-format",
                "error_as_warning",
            ):
                raise CheckFailed(f"{unformatted} Terraform file(s) need formatting")


def run_terraform_validation(session: Any) -> None:
    """Run Checkov against Terraform files."""
    if not in_container():
        session.install("checkov==3.2.268")
    root = workspace_from(session.invoked_from)
    with session.chdir(root):
        with wrap(
            session,
            "Terraform validation failed",
            "terraform-validation",
            "error_as_warning",
        ):
            session.run(
                "checkov",
                "--directory",
                ".",
                "--framework",
                "terraform",
                "--skip-path",
                "repos",
                "--skip-download",
                external=in_container(),
            )
