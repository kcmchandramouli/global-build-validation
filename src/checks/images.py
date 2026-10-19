"""Unreferenced image analysis."""

from __future__ import annotations

import os
import subprocess
from functools import lru_cache
from pathlib import Path
from typing import Any, Optional

from src.config import as_bool, find_config_file, get_config_value
from src.output import ci, info

IMAGE_EXTENSIONS = (".jpg", ".jpeg", ".png", ".gif")


def _configuration(*config_path: str) -> Optional[bool]:
    """Read a nested boolean from the consumer config file."""
    configuration_file = find_config_file()
    if configuration_file is None:
        info("No build-validation.yml found.")
        return None
    info(f"Reading configuration file {configuration_file!s}...")
    return as_bool(get_config_value(*config_path))


@lru_cache(maxsize=None)
def _read_file(filepath: Path) -> str:
    """Read a text file, ignoring binary files."""
    try:
        return filepath.read_text(encoding="utf-8")
    except UnicodeDecodeError:
        return ""


def _tracked_files() -> list[Path]:
    """Return paths tracked by git."""
    git_output = subprocess.check_output(["git", "ls-files"], text=True)
    return [Path(file) for file in git_output.strip().split("\n") if file]


def scan_unreferenced_images() -> int:
    """Return 0 when every tracked image is referenced, else 1."""
    tracked_files = _tracked_files()
    image_files = [
        file for file in tracked_files if file.suffix.lower() in IMAGE_EXTENSIONS
    ]
    files_to_search = [
        file
        for file in tracked_files
        if file.suffix.lower() not in IMAGE_EXTENSIONS
        and not file.name.startswith(".git")
    ]

    def is_referenced(img_filename: str) -> bool:
        for filepath in files_to_search:
            if img_filename in _read_file(filepath):
                info(f"Found reference in {filepath}")
                return True
        return False

    found_unreferenced_image = False
    for img_file in image_files:
        info(f"Searching image {img_file.name}...")
        if not is_referenced(img_file.name):
            ci(f"::warning::Found unreferenced image {img_file}")
            ci(
                "##vso[task.logissue type=warning]"
                f"Found unreferenced image {img_file}"
            )
            found_unreferenced_image = True

    if not found_unreferenced_image:
        info("No unreferenced images found.")
        return 0

    warning = _configuration("unreferenced-image-check", "error_as_warning")
    if warning is None:
        warning = os.getenv("ERROR_AS_WARNING", "true").casefold() == "true"
    message = "Found unreferenced images"
    if warning:
        ci(f"::warning::{message} (warn only)")
        ci(f"##vso[task.logissue type=warning]{message} (warn only)")
        ci("##vso[task.complete result=SucceededWithIssues]")
        return 0
    ci(f"::error::{message}")
    ci(f"##vso[task.logissue type=error]{message}")
    ci("##vso[task.complete result=Failed]")
    return 1


def run_unreferenced_images(session: Any) -> None:
    """Fail when tracked images are not referenced."""
    with session.chdir(session.invoked_from):
        if scan_unreferenced_images() != 0:
            session.error("Found unreferenced images")
