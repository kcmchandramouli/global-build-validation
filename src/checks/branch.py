"""Git branch name analysis."""

from __future__ import annotations

import os
import re
import subprocess
from typing import Any

from src.config import error_as_warning, get_config_value
from src.runner import report

DEFAULT_BRANCH_REGEX = (
    r"^(main|master|develop|(feature|feat|fix|hotfix|release|chore)"
    r"/[A-Za-z0-9._-]+)$"
)


def normalize_branch(branch: str) -> str:
    """Strip git ref prefixes."""
    return branch.replace("refs/heads/", "").replace("refs/pull/", "")


def branch_is_valid(branch: str, pattern: str) -> bool:
    """Return True when the whole branch name matches the pattern."""
    return re.search(pattern, branch) is not None


def current_branch() -> str:
    """Return BRANCH_TO_CHECK, or the current git branch."""
    configured = os.environ.get("BRANCH_TO_CHECK", "")
    if configured:
        return normalize_branch(configured)
    result = subprocess.run(
        ["git", "rev-parse", "--abbrev-ref", "HEAD"],
        check=False,
        capture_output=True,
        text=True,
    )
    if result.returncode != 0:
        return ""
    name = result.stdout.strip()
    if name == "HEAD":
        return ""
    return name


def run_branch_name(session: Any) -> None:
    """Validate BRANCH_TO_CHECK, or the current git branch."""
    configured = get_config_value("branch-name-validation", "branch_regex")
    if isinstance(configured, str) and configured:
        session.log("Using regular expression from build-validation.yml")
        pattern = configured
    else:
        pattern = (
            os.environ.get("BRANCH_NAME_REGULAR_EXPRESSION") or DEFAULT_BRANCH_REGEX
        )
    branch = current_branch()
    try:
        valid = branch_is_valid(branch, pattern)
    except re.error as exc:
        report(
            session,
            f"Invalid branch regular expression: {exc}",
            False,
            str(exc),
        )
        return
    if valid:
        session.log(f"Branch name [{branch}] follows regular expression >>{pattern}<<")
        return
    report(
        session,
        (
            f"Branch name [{branch}] does not follow regular expression "
            f">>{pattern}<<"
        ),
        error_as_warning("branch-name-validation", "error_as_warning"),
        "branch name validation failed",
    )
