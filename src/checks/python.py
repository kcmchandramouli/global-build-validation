"""Python analysis sessions: black, flake8, ruff, pylint, mypy, pytest."""

from __future__ import annotations

import contextlib
import os
import pathlib
from typing import Any, Generator

import nox

from src.config import as_bool, error_as_warning, find_config_file, get_config_value
from src.runner import report
from src.workspace import SHARE, in_container

CONTAINER_CONFIG_DIR = pathlib.Path("/etc/python-validation")
LOCAL_CONFIG_DIR = SHARE / "python-validation"
MODIFIED_FILES = pathlib.Path("/tmp/python.files")

# Keep these pins aligned with requirements.txt.
CHECKER_PACKAGES: dict[str, tuple[str, ...]] = {
    "black": ("black~=24.4.2",),
    "flake8": ("flake8~=7.0.0", "flake8-print~=5.0.0"),
    "ruff": ("ruff~=0.4.7",),
    "pylint": ("pylint~=3.1.0", "pylint-junit==0.3.4"),
    "mypy": ("mypy~=1.10.0",),
    "pytest": ("pytest~=8.2.0", "pytest-timeout~=2.3.1", "pytest-cov~=5.0.0"),
}


def tool_config_dir() -> pathlib.Path:
    """Return checker config dir (image path, else this checkout)."""
    if CONTAINER_CONFIG_DIR.is_dir():
        return CONTAINER_CONFIG_DIR
    return LOCAL_CONFIG_DIR


def prepare_checker(session: Any, name: str) -> bool:
    """Install checker packages when they are not already in the image.

    Returns True when commands should use the image PATH.
    """
    external = in_container() or CONTAINER_CONFIG_DIR.is_dir()
    if not external:
        session.install(*CHECKER_PACKAGES[name])
    return external


def _modified_or_default(*default: str) -> list[str]:
    """Return modified Python files when CI wrote the list."""
    if MODIFIED_FILES.exists():
        return [
            line
            for line in MODIFIED_FILES.read_text(encoding="utf-8").split("\n")
            if line != ""
        ]
    return list(default)


def _working_directory(session: Any) -> pathlib.Path:
    """Use the invocation directory inside an image."""
    if os.getenv("DOCKER_ENTRYPOINT") is None:
        return pathlib.Path(".")
    return pathlib.Path(session.invoked_from)


def _configuration(session: Any, *config_path: str) -> Any:
    """Read nested configuration from the consumer repository."""
    working_directory = _working_directory(session)
    configuration_file = find_config_file(working_directory)
    if configuration_file is None:
        session.log("No build-validation.yml found.")
        return None
    session.log(f"Reading configuration file {configuration_file!s}...")
    value = get_config_value(*config_path, config_dir=working_directory)
    coerced = as_bool(value)
    return coerced if coerced is not None else value


def _check_upload_junit(session: Any, *config_path: str) -> None:
    """Honor upload_junit from consumer config."""
    upload_junit = _configuration(session, *config_path)
    if isinstance(upload_junit, bool):
        value = str(upload_junit).lower()
        print(f"##vso[task.setvariable variable=UploadJunit]{value}")  # noqa: T201


@contextlib.contextmanager
def _wrap(session: Any, *config_path: str) -> Generator[None, None, None]:
    """Convert failures to warnings when configured."""
    try:
        if config_path[-1] in ("pytest", "pylint"):
            _check_upload_junit(session, *config_path, "upload_junit")
        yield
    except nox.command.CommandFailed as exc:
        report(
            session,
            f"Session {session.name} failed",
            error_as_warning(*config_path, "error_as_warning"),
            str(exc),
        )


def _install_consumer_packages(session: Any) -> None:
    """Install consumer requirements into the session environment."""
    if pathlib.Path("requirements.txt").exists():
        session.install("-r", "requirements.txt")
    if pathlib.Path("setup.py").exists():
        session.install(".")


def _repository_has_tests(root: pathlib.Path) -> bool:
    """Return True when the repository contains pytest modules."""
    skipped = {".git", "repos", "htmlcov", "__pycache__", ".pytest_cache"}
    for _directory, dirnames, filenames in os.walk(root):
        dirnames[:] = [
            name
            for name in dirnames
            if name not in skipped and not name.startswith((".nox", ".venv"))
        ]
        for name in filenames:
            if name.startswith("test_") and name.endswith(".py"):
                return True
            if name.endswith("_test.py"):
                return True
    return False


def black(session: Any) -> None:
    """Run black in check mode."""
    external = prepare_checker(session, "black")
    with session.chdir(session.invoked_from):
        files = session.posargs or _modified_or_default(".")
        if not files:
            session.skip("No files to check")
        args = ["--diff", "--check", "--extend-exclude", "repos/", *files]
        with _wrap(session, "python", "black"):
            session.run("black", *args, external=external)


def flake8(session: Any) -> None:
    """Run flake8."""
    external = prepare_checker(session, "flake8")
    with session.chdir(session.invoked_from):
        files = session.posargs or _modified_or_default(".")
        if not files:
            session.skip("No files to check")
        with _wrap(session, "python", "flake8"):
            session.run(
                "flake8",
                "--config",
                str(tool_config_dir() / "flake8.ini"),
                *files,
                external=external,
            )


def ruff(session: Any) -> None:
    """Run ruff."""
    external = prepare_checker(session, "ruff")
    with session.chdir(session.invoked_from):
        files = session.posargs or _modified_or_default(".")
        if not files:
            session.skip("No files to check")
        with _wrap(session, "python", "ruff"):
            session.run(
                "ruff",
                "check",
                "--config",
                str(tool_config_dir() / "pyproject.toml"),
                *files,
                external=external,
            )


def pylint(session: Any) -> None:
    """Run pylint."""
    external = prepare_checker(session, "pylint")
    if not external:
        # Let pylint resolve imports used by this package.
        session.install("pyyaml", "nox>=2024.4.15", "requests==2.32.3")
    working_directory = _working_directory(session)
    with session.chdir(working_directory):
        pylint_rc = working_directory / "pylint.rc"
        if not pylint_rc.exists():
            pylint_rc = tool_config_dir() / "pylint.rc"
        files = session.posargs or _modified_or_default(".")
        if not files:
            session.skip("No files to check")
        report_path = working_directory / "pylint.results.xml"
        args = [
            f"--rcfile={pylint_rc}",
            f"--output-format=pylint_junit.JUnitReporter:{report_path},text",
            "--recursive=y",
            *files,
        ]
        with _wrap(session, "python", "pylint"):
            _install_consumer_packages(session)
            session.run("pylint", *args, external=external)


def mypy(session: Any) -> None:
    """Run mypy."""
    external = prepare_checker(session, "mypy")
    with session.chdir(session.invoked_from):
        files = session.posargs or _modified_or_default(".")
        if not files:
            session.skip("No files to check")
        with _wrap(session, "python", "mypy"):
            session.run(
                "mypy",
                "--config-file",
                str(tool_config_dir() / "pyproject.toml"),
                "--install-types",
                "--non-interactive",
                *files,
                external=external,
            )


def pytest(session: Any) -> None:
    """Run pytest with coverage."""
    external = prepare_checker(session, "pytest")
    if not external:
        session.install("pyyaml", "nox>=2024.4.15", "requests==2.32.3")
    working_directory = _working_directory(session)
    with session.chdir(working_directory):
        session.env["COVERAGE_FILE"] = str(working_directory / ".coverage")
        args = session.posargs or [
            "-v",
            f"--cov-config={tool_config_dir() / 'pytest-coverage.rc'}",
            "--cov=./",
            "--cov-report=html",
            "--junit-xml=pytest.results.xml",
            "--timeout=60",
            "--doctest-modules",
            "--ignore-glob=repos/*",
            "--ignore-glob=noxfile.py",
        ]
        if not session.posargs and not _repository_has_tests(pathlib.Path(".")):
            args.append("--cov-fail-under=0")
        with _wrap(session, "python", "pytest"):
            _install_consumer_packages(session)
            session.run("pytest", *args, external=external, success_codes=[0, 5])
