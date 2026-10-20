"""Git branch name analysis."""

from __future__ import annotations

import os
import re
import subprocess
from typing import Any

from src.config import error_as_warning, get_config_value
from src.runner import report

DEFAULT_BRANCH_REGEX = (
    r"^(task|feature)/(main|master|develop|maintenance|staging|prod)"
    r"/[A-Za-z0-9._-]+$"
)

# Integration branches are not task or feature work. Tags are releases, not
# branch names. The pattern above applies only to task and feature branches.
EXEMPT_BRANCHES = frozenset({"main", "master"})


def normalize_branch(branch: str) -> str:
    """Strip git ref prefixes."""
    if branch.startswith("refs/tags/"):
        return branch[len("refs/tags/") :]
    return branch.replace("refs/heads/", "").replace("refs/pull/", "")


def branch_is_valid(branch: str, pattern: str) -> bool:
    """Return True when the whole branch name matches the pattern."""
    return re.search(pattern, branch) is not None


def _git(*args: str) -> subprocess.CompletedProcess[str]:
    """Run git and capture its output without raising."""
    return subprocess.run(
        ["git", *args],
        check=False,
        capture_output=True,
        text=True,
    )


def _ref_exists(ref: str) -> bool:
    """Return True when git can resolve the ref."""
    return _git("rev-parse", "--verify", "--quiet", "--", ref).returncode == 0


def _ci_tag_name() -> str:
    """Return the tag name when the CI event is a tag, otherwise empty."""
    if os.environ.get("GITHUB_REF_TYPE") == "tag":
        name = os.environ.get("GITHUB_REF_NAME", "")
        if name:
            return name
    for key in ("BUILD_SOURCEBRANCH", "GITHUB_REF"):
        ref = os.environ.get(key, "")
        if ref.startswith("refs/tags/"):
            return ref[len("refs/tags/") :]
    return ""


def is_tag(raw: str, name: str) -> bool:
    """Return True when the ref being checked is a git tag."""
    if raw.startswith("refs/tags/"):
        return True
    ci_tag = _ci_tag_name()
    if ci_tag and name == ci_tag:
        return True
    if not name:
        return False
    # A bare name that exists only as a tag is a tag. A name that is also a
    # branch stays a branch so task and feature rules still apply.
    return _ref_exists(f"refs/tags/{name}") and not _ref_exists(f"refs/heads/{name}")


def current_ref() -> tuple[str, str]:
    """Return ``(raw, name)`` for BRANCH_TO_CHECK or the current checkout.

    ``raw`` is the unstripped value. ``name`` has ref prefixes removed.
    A detached HEAD that points at a tag is returned as that tag. A detached
    HEAD that is not a tag yields an empty name.
    """
    configured = os.environ.get("BRANCH_TO_CHECK", "")
    if configured:
        return configured, normalize_branch(configured)
    result = _git("rev-parse", "--abbrev-ref", "HEAD")
    if result.returncode != 0:
        return "", ""
    name = result.stdout.strip()
    if name != "HEAD":
        return name, name
    described = _git("describe", "--exact-match", "--tags", "HEAD")
    if described.returncode == 0:
        tag = described.stdout.strip()
        return f"refs/tags/{tag}", tag
    # Checkout of a tag is detached. CI still records the tag when the tag
    # object itself was not fetched.
    ci_tag = _ci_tag_name()
    if ci_tag:
        return f"refs/tags/{ci_tag}", ci_tag
    return "", ""


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
    raw, branch = current_ref()
    if branch in EXEMPT_BRANCHES:
        session.log(
            f"Branch name [{branch}] is allowed without the task/feature pattern"
        )
        return
    if is_tag(raw, branch):
        session.log(f"Tag [{branch}] is allowed without the task/feature pattern")
        return
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
