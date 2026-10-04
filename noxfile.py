"""Nox sessions for analysis.

Every analysis check is implemented in the src package and started here.
"""

from __future__ import annotations

import pathlib
import sys

import nox

ROOT = pathlib.Path(__file__).resolve().parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from src.checks.branch import run_branch_name  # noqa: E402
from src.checks.images import run_unreferenced_images  # noqa: E402
from src.checks.markup import (  # noqa: E402
    run_markdown_link_check,
    run_markdownlint,
    run_prettier,
)
from src.checks.python import black as run_black  # noqa: E402
from src.checks.python import flake8 as run_flake8  # noqa: E402
from src.checks.python import mypy as run_mypy  # noqa: E402
from src.checks.python import pylint as run_pylint  # noqa: E402
from src.checks.python import pytest as run_pytest  # noqa: E402
from src.checks.python import ruff as run_ruff  # noqa: E402
from src.checks.spelling import run_cspell  # noqa: E402
from src.checks.terraform import (  # noqa: E402
    run_terraform_format,
    run_terraform_validation,
)
from src.checks.yaml import run_yamllint  # noqa: E402

PYTHON_SESSIONS = ("black", "flake8", "ruff", "pylint", "mypy", "pytest")
ANALYSIS_SESSIONS = (
    *PYTHON_SESSIONS,
    "markdownlint",
    "markdown-link-check",
    "prettier",
    "yamllint",
    "cspell",
    "terraform-format",
    "terraform-validation",
    "unreferenced-image-check",
    "branch-name",
)

nox.options.sessions = []


@nox.session(reuse_venv=True)
def black(session: nox.Session) -> None:
    """Check Python formatting. Usage: nox -s black -- ."""
    run_black(session)


@nox.session(reuse_venv=True)
def flake8(session: nox.Session) -> None:
    """Run flake8. Usage: nox -s flake8 -- ."""
    run_flake8(session)


@nox.session(reuse_venv=True)
def ruff(session: nox.Session) -> None:
    """Run ruff. Usage: nox -s ruff -- ."""
    run_ruff(session)


@nox.session(reuse_venv=True)
def pylint(session: nox.Session) -> None:
    """Run pylint. Usage: nox -s pylint -- ."""
    run_pylint(session)


@nox.session(reuse_venv=True)
def mypy(session: nox.Session) -> None:
    """Run mypy. Usage: nox -s mypy -- ."""
    run_mypy(session)


@nox.session(reuse_venv=True)
def pytest(session: nox.Session) -> None:
    """Run pytest with coverage. Usage: nox -s pytest."""
    run_pytest(session)


@nox.session(python=False)
def python(session: nox.Session) -> None:
    """Run all Python checkers. Usage: nox -s python -- ."""
    for name in PYTHON_SESSIONS:
        session.notify(name, session.posargs)


@nox.session(reuse_venv=True)
def yamllint(session: nox.Session) -> None:
    """Lint YAML files. Usage: nox -s yamllint -- ."""
    run_yamllint(session)


@nox.session(python=False)
def cspell(session: nox.Session) -> None:
    """Spell-check files. Usage: nox -s cspell."""
    run_cspell(session)


@nox.session(python=False)
def markdownlint(session: nox.Session) -> None:
    """Lint Markdown. Usage: nox -s markdownlint."""
    run_markdownlint(session)


@nox.session(python=False, name="markdown-link-check")
def markdown_link_check(session: nox.Session) -> None:
    """Check links in Markdown. Usage: nox -s markdown-link-check."""
    run_markdown_link_check(session)


@nox.session(python=False)
def prettier(session: nox.Session) -> None:
    """Check Markdown, YAML, and TOML formatting. Usage: nox -s prettier."""
    run_prettier(session)


@nox.session(python=False, name="terraform-format")
def terraform_format(session: nox.Session) -> None:
    """Check Terraform formatting. Usage: nox -s terraform-format."""
    run_terraform_format(session)


@nox.session(reuse_venv=True, name="terraform-validation")
def terraform_validation(session: nox.Session) -> None:
    """Run Checkov on Terraform. Usage: nox -s terraform-validation."""
    run_terraform_validation(session)


@nox.session(reuse_venv=True, name="unreferenced-image-check")
def unreferenced_image_check(session: nox.Session) -> None:
    """Find images that nothing references. Usage: nox -s unreferenced-image-check."""
    run_unreferenced_images(session)


@nox.session(python=False, name="branch-name")
def branch_name(session: nox.Session) -> None:
    """Validate the git branch name. Usage: nox -s branch-name."""
    run_branch_name(session)


@nox.session(python=False)
def analyze(session: nox.Session) -> None:
    """Run every analysis session. Usage: nox -s analyze."""
    if session.posargs:
        session.error("Pass paths to one session, for example: nox -s yamllint -- .")
    for name in ANALYSIS_SESSIONS:
        session.notify(name)
