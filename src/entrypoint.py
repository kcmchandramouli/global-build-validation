"""Container entrypoint. Analysis always starts a nox session."""

from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path

NOXFILE_ENV = "GBV_NOXFILE"
DEFAULT_SESSION_ENV = "GBV_DEFAULT_SESSION"
DEFAULT_NOXFILE = str(Path(__file__).resolve().parents[1] / "noxfile.py")


def prepare_home() -> None:
    """Give tools a writable HOME inside the image."""
    home = os.environ.get("HOME", "")
    if home and home != "/home/" and Path(home).is_dir():
        return
    fallback = os.environ.get("DOCKER_WORKDIR", "/workspace")
    os.environ["HOME"] = fallback if Path(fallback).is_dir() else "/tmp"


def build_nox_command(
    argv: list[str],
    *,
    noxfile: str,
    default_session: str,
    executable: str,
) -> list[str] | None:
    """Return a nox command, or None when argv is an external program."""
    if argv and not argv[0].startswith("-"):
        return None
    command = [
        executable,
        "-m",
        "nox",
        "--noxfile",
        noxfile,
        "--no-venv",
        "--non-interactive",
        "--forcecolor",
    ]
    if argv:
        command.extend(argv)
    elif default_session:
        command.extend(["-s", default_session])
    return command


def emit_ci_toolchain() -> None:
    """Print installed tool versions when Azure Pipelines set TF_BUILD."""
    if os.environ.get("TF_BUILD", "").casefold() != "true":
        return
    _dump_group("Dump python packages", [sys.executable, "-m", "pip", "freeze"])


def _dump_group(title: str, command: list[str]) -> None:
    """Print an Azure log group around a best-effort version command."""
    print(f"##[group]{title}", flush=True)  # noqa: T201
    subprocess.run(command, check=False)
    print("##[endgroup]", flush=True)  # noqa: T201


def main(argv: list[str] | None = None) -> int:
    """Start nox, or replace this process with an explicit command."""
    args = list(sys.argv[1:] if argv is None else argv)
    prepare_home()
    if args and not args[0].startswith("-"):
        os.execvp(args[0], args)
    default_session = os.environ.get(DEFAULT_SESSION_ENV, "")
    if not args and not default_session:
        print(  # noqa: T201
            "Pass a nox session, for example: python3 -m src.entrypoint -s yamllint",
            file=sys.stderr,
        )
        return 2
    command = build_nox_command(
        args,
        noxfile=os.environ.get(NOXFILE_ENV, DEFAULT_NOXFILE),
        default_session=default_session,
        executable=sys.executable,
    )
    if command is None:
        return 2
    os.environ["DOCKER_ENTRYPOINT"] = "1"
    emit_ci_toolchain()
    os.execv(command[0], command)
    return 1


if __name__ == "__main__":
    sys.exit(main())
