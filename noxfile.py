"""Local helpers for building and running checker images."""

from __future__ import annotations

import os
import pathlib
import subprocess

import nox
import yaml

ROOT = pathlib.Path(__file__).parent.resolve()
CATALOG = ROOT / "images" / "catalog.yml"

nox.options.sessions = ["list_images"]


def _images() -> list[dict[str, str]]:
    with CATALOG.open(encoding="utf-8") as handle:
        return yaml.safe_load(handle)["images"]


def _registry() -> str:
    return os.environ.get("GBV_IMAGE_REGISTRY", "global-build-validation")


@nox.session(python=False)
def list_images(session: nox.Session) -> None:
    """Print checker image tags."""
    for image in _images():
        session.log(f"{image['tag']:32} {image['dockerfile']}")


@nox.session(python=False)
def build_image(session: nox.Session) -> None:
    """Build one image: nox -s build_image -- python-validation.v1"""
    if not session.posargs:
        session.error("Pass an image tag, for example: nox -s build_image -- yamllint.v1")
    tag = session.posargs[0]
    match = next((item for item in _images() if item["tag"] == tag), None)
    if match is None:
        session.error(f"Unknown tag {tag!r}. Run: nox -s list_images")
    image = f"{_registry()}:{tag}"
    session.run(
        "docker",
        "build",
        "-f",
        match["dockerfile"],
        "-t",
        image,
        ".",
        external=True,
    )


@nox.session(python=False)
def build_all(session: nox.Session) -> None:
    """Build every checker image."""
    for image in _images():
        session.notify("build_image", [image["tag"]])


def _host_workspace() -> str:
    """Return the repo root in a form Docker Desktop accepts on Windows."""
    host_root = str(ROOT)
    if os.name == "nt":
        return host_root.replace("\\", "/")
    return host_root


@nox.session(python=False)
def run_check(session: nox.Session) -> None:
    """Run a checker image against this repository (Windows and Unix)."""
    if not session.posargs:
        session.error("Pass an image tag, for example: nox -s run_check -- yamllint.v1")
    tag, *args = session.posargs
    if tag not in {item["tag"] for item in _images()}:
        session.error(f"Unknown tag {tag!r}. Run: nox -s list_images")

    image = f"{_registry()}:{tag}"
    inspect = subprocess.run(
        ["docker", "image", "inspect", image],
        check=False,
        capture_output=True,
        text=True,
    )
    if inspect.returncode != 0:
        session.error(
            f"Image {image} not found locally. Build it with: nox -s build_image -- {tag}"
        )

    session.run(
        "docker",
        "run",
        "--rm",
        "-e",
        f"ERROR_AS_WARNING={os.environ.get('ERROR_AS_WARNING', 'false')}",
        "-e",
        f"BRANCH_TO_CHECK={os.environ.get('BRANCH_TO_CHECK', '')}",
        "-e",
        f"TF_BUILD={os.environ.get('TF_BUILD', '')}",
        "-v",
        f"{_host_workspace()}:/workspace",
        "-w",
        "/workspace",
        "--entrypoint",
        "/usr/local/bin/docker_entrypoint.sh",
        image,
        *args,
        external=True,
    )


@nox.session
def test(session: nox.Session) -> None:
    """Run unit tests for config helpers (no Docker required)."""
    session.install("pyyaml", "pytest")
    session.run("pytest", "-q", "tests")


@nox.session(python=False)
def helm_lint(session: nox.Session) -> None:
    """Lint Helm charts."""
    session.run("helm", "lint", "helm/agent", external=True)
    session.run(
        "helm",
        "lint",
        "helm/secrets",
        "--values",
        "helm/secrets/values.example.yaml",
        external=True,
    )
