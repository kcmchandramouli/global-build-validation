#!/usr/bin/env nox
"""Python validation sessions used inside the checker image."""

from __future__ import annotations

import contextlib
import os
import pathlib
import sys
from typing import Any, Generator, List, Union

import nox

THIS_DIRECTORY = pathlib.Path(__file__).parent.resolve()
MODIFIED_FILES = pathlib.Path("/tmp/python.files")
CONTAINER_CONFIG_DIR = pathlib.Path("/etc/python-validation")

nox.options.sessions = []


def _ensure_read_config() -> None:
    """Put images/common or the image copy of read_config.py on sys.path."""
    if "read_config" in sys.modules:
        return
    candidates = [
        THIS_DIRECTORY.parent / "common",
        pathlib.Path("/usr/local/bin"),
        pathlib.Path("/usr/local/lib/gbv"),
    ]
    for directory in candidates:
        if (directory / "read_config.py").is_file():
            sys.path.insert(0, str(directory))
            return


def tool_config_dir() -> pathlib.Path:
    """Return checker config dir (image path, else this checkout)."""
    if CONTAINER_CONFIG_DIR.is_dir():
        return CONTAINER_CONFIG_DIR
    return THIS_DIRECTORY


def get_modified_files_or_default(*default: str) -> List[str]:
    """Return the list of modified files if present, else the default."""
    if MODIFIED_FILES.exists():
        return [
            line
            for line in MODIFIED_FILES.read_text(encoding="utf-8").split("\n")
            if line != ""
        ]
    return list(default)


def get_working_directory(session: nox.Session) -> pathlib.Path:
    """Get the working directory to use."""
    if os.getenv("DOCKER_ENTRYPOINT") is None:
        return pathlib.Path(".")
    return pathlib.Path(session.invoked_from)


def get_configuration(
    session: nox.Session, *config_path: str
) -> Union[dict[Any, str], str, bool, None]:
    """Read nested configuration from the consumer repository."""
    _ensure_read_config()
    import read_config

    working_directory = get_working_directory(session)
    configuration_file = read_config.find_config_file(working_directory)
    if configuration_file is None:
        session.log("No build-validation.yml found.")
        return None

    session.log(f"Reading configuration file {configuration_file!s}...")
    value = read_config.get_config_value(*config_path, config_dir=working_directory)
    coerced = read_config.as_bool(value)
    return coerced if coerced is not None else value


def check_upload_junit(session: nox.Session, *config_path: str) -> None:
    """Honor upload_junit from consumer config."""
    upload_junit = get_configuration(session, *config_path)
    if isinstance(upload_junit, bool):
        value = str(upload_junit).lower()
        print(f"##vso[task.setvariable variable=UploadJunit]{value}")


@contextlib.contextmanager
def wrap_command(session: nox.Session, *config_path: str) -> Generator:
    """Convert failures to warnings when configured."""
    try:
        if config_path[-1] in ["pytest", "pylint"]:
            check_upload_junit(session, *config_path, "upload_junit")
        yield
    except nox.command.CommandFailed as exc:
        error_as_warning = get_configuration(session, *config_path, "error_as_warning")
        if error_as_warning is None:
            env_value = os.getenv("ERROR_AS_WARNING")
            error_as_warning = (
                env_value.casefold() == "true" if env_value is not None else False
            )
        message = f"Session {session.name} failed"
        if error_as_warning:
            session.warn(
                f"{message}: {exc} (warn only)\n"
                f"::warning::{message}\n"
                f"##vso[task.logissue type=warning]{message}\n"
                "##vso[task.complete result=SucceededWithIssues]"
            )
        else:
            session.error(
                f"{exc}\n::error::{message}\n"
                f"##vso[task.logissue type=error]{message}\n"
                "##vso[task.complete result=Failed]"
            )


def install_python_modules(session: nox.Session) -> None:
    """Install consumer requirements if present."""
    if pathlib.Path("requirements.txt").exists():
        session.run(sys.executable, "-m", "pip", "install", "-r", "requirements.txt")
    if pathlib.Path("setup.py").exists() or pathlib.Path("pyproject.toml").exists():
        if pathlib.Path("setup.py").exists():
            session.run(sys.executable, "-m", "pip", "install", ".")


@nox.session(python=False)
def black(session: nox.Session) -> None:
    """Run black in check mode."""
    with session.chdir(session.invoked_from):
        files = session.posargs or get_modified_files_or_default(".")
        if not files:
            session.skip("No files to check")
        args = ["--diff", "--check", "--extend-exclude", "repos/", *files]
        with wrap_command(session, "python", "black"):
            session.run("black", *args, external=True)


@nox.session(python=False)
def flake8(session: nox.Session) -> None:
    """Run flake8."""
    with session.chdir(session.invoked_from):
        files = session.posargs or get_modified_files_or_default(".")
        if not files:
            session.skip("No files to check")
        with wrap_command(session, "python", "flake8"):
            session.run(
                "flake8",
                "--config",
                str(tool_config_dir() / "flake8.ini"),
                *files,
                external=True,
            )


@nox.session(python=False)
def ruff(session: nox.Session) -> None:
    """Run ruff."""
    with session.chdir(session.invoked_from):
        files = session.posargs or get_modified_files_or_default(".")
        if not files:
            session.skip("No files to check")
        with wrap_command(session, "python", "ruff"):
            session.run(
                "ruff",
                "check",
                "--config",
                str(tool_config_dir() / "pyproject.toml"),
                *files,
                external=True,
            )


@nox.session
def pylint(session: nox.Session) -> None:
    """Run pylint."""
    working_directory = get_working_directory(session)
    with session.chdir(working_directory):
        pylint_rc = working_directory / "pylint.rc"
        if not pylint_rc.exists():
            pylint_rc = tool_config_dir() / "pylint.rc"
        files = session.posargs or get_modified_files_or_default(".")
        if not files:
            session.skip("No files to check")
        args = [
            f"--rcfile={pylint_rc}",
            f"--output-format=pylint_junit.JUnitReporter:{working_directory / 'pylint.results.xml'},text",
            "--recursive=y",
            *files,
        ]
        with wrap_command(session, "python", "pylint"):
            install_python_modules(session)
            session.run("pylint", *args, external=True)


@nox.session(python=False)
def mypy(session: nox.Session) -> None:
    """Run mypy."""
    with session.chdir(session.invoked_from):
        files = session.posargs or get_modified_files_or_default(".")
        if not files:
            session.skip("No files to check")
        with wrap_command(session, "python", "mypy"):
            session.run(
                "mypy",
                "--config-file",
                str(tool_config_dir() / "pyproject.toml"),
                "--install-types",
                "--non-interactive",
                *files,
                external=True,
            )


@nox.session
def pytest(session: nox.Session) -> None:
    """Run pytest with coverage."""
    working_directory = get_working_directory(session)
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
        with wrap_command(session, "python", "pytest"):
            install_python_modules(session)
            session.run("pytest", *args, external=True, success_codes=[0, 5])
