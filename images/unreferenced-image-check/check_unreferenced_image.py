"""Check for unreferenced images in the git repository."""

from __future__ import annotations

import os
import subprocess
import sys
from functools import lru_cache
from pathlib import Path
from typing import Optional


def _ensure_read_config() -> None:
    """Put images/common or the image copy of read_config.py on sys.path."""
    if "read_config" in sys.modules:
        return
    candidates = [
        Path(__file__).resolve().parent.parent / "common",
        Path("/usr/local/bin"),
        Path("/usr/local/lib/gbv"),
    ]
    for directory in candidates:
        if (directory / "read_config.py").is_file():
            sys.path.insert(0, str(directory))
            return


_ensure_read_config()
import read_config  # noqa: E402

IMAGE_EXTENSIONS = [".jpg", ".jpeg", ".png", ".gif"]


def _print(message: str) -> None:
    """Print a message immediately."""
    print(message, flush=True)


def get_configuration(*config_path: str) -> Optional[bool]:
    """Read a nested boolean from the consumer config file."""
    configuration_file = read_config.find_config_file()
    if configuration_file is None:
        _print("No build-validation.yml found.")
        return None

    _print(f"Reading configuration file {configuration_file!s}...")
    return read_config.as_bool(read_config.get_config_value(*config_path))


@lru_cache(maxsize=None)
def read_file_contents(filepath: Path) -> str:
    """Read a text file, ignoring binary files."""
    try:
        return filepath.read_text(encoding="utf-8")
    except UnicodeDecodeError:
        return ""


def find_git_tracked_files() -> list[Path]:
    """Find all files tracked by git."""
    git_output = subprocess.check_output(["git", "ls-files"], text=True)
    return [Path(file) for file in git_output.strip().split("\n") if file]


def main() -> int:
    """Check for unreferenced images in the git repository."""
    tracked_files = find_git_tracked_files()
    image_files = [
        file for file in tracked_files if file.suffix.lower() in IMAGE_EXTENSIONS
    ]
    files_to_search = [
        file
        for file in tracked_files
        if file.suffix.lower() not in IMAGE_EXTENSIONS and not file.name.startswith(".git")
    ]

    def is_image_referenced(img_filename: str) -> bool:
        for filepath in files_to_search:
            if img_filename in read_file_contents(filepath):
                _print(f"Found reference in {filepath}")
                return True
        return False

    found_unreferenced_image = False
    for img_file in image_files:
        _print(f"\nSearching image {img_file.name}...")
        if not is_image_referenced(img_file.name):
            _print(f"::warning::Found unreferenced image {img_file}")
            _print(f"##vso[task.logissue type=warning]Found unreferenced image {img_file}")
            found_unreferenced_image = True

    if found_unreferenced_image:
        error_as_warning = get_configuration("unreferenced-image-check", "error_as_warning")
        if error_as_warning is None:
            error_as_warning = os.getenv("ERROR_AS_WARNING", "true").casefold() == "true"
        message = "Found unreferenced images"
        if error_as_warning:
            _print(f"::warning::{message} (warn only)")
            _print(f"##vso[task.logissue type=warning]{message} (warn only)")
            _print("##vso[task.complete result=SucceededWithIssues]")
            return 0
        _print(f"::error::{message}")
        _print(f"##vso[task.logissue type=error]{message}")
        _print("##vso[task.complete result=Failed]")
        return 1

    _print("No unreferenced images found.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
