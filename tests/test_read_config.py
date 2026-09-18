"""Local tests for consumer config loading."""

from __future__ import annotations

import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
COMMON = ROOT / "images" / "common"
if str(COMMON) not in sys.path:
    sys.path.insert(0, str(COMMON))

import read_config  # noqa: E402

LEGACY_CONFIG_NAME = "sw4zf" + ".yml"


@pytest.fixture
def config_dir(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    """Run each test in an empty directory without GBV_CONFIG_FILE."""
    monkeypatch.chdir(tmp_path)
    monkeypatch.delenv(read_config.CONFIG_FILE_ENV, raising=False)
    return tmp_path


def test_loads_build_validation_yml(config_dir: Path) -> None:
    """Read nested values from build-validation.yml in the working directory."""
    (config_dir / "build-validation.yml").write_text(
        "build-validation:\n  yamllint:\n    error_as_warning: false\n",
        encoding="utf-8",
    )
    assert read_config.get_config_value("yamllint", "error_as_warning") is False


def test_ignores_legacy_vendor_config_file(config_dir: Path) -> None:
    """Do not load the retired vendor config filename."""
    (config_dir / LEGACY_CONFIG_NAME).write_text(
        "build-validation:\n  yamllint:\n    error_as_warning: true\n",
        encoding="utf-8",
    )
    assert read_config.find_config_file() is None
    assert read_config.get_config_value("yamllint", "error_as_warning") is None


def test_prefers_build_validation_over_legacy(config_dir: Path) -> None:
    """Prefer build-validation.yml when both files exist."""
    (config_dir / "build-validation.yml").write_text(
        "build-validation:\n  yamllint:\n    error_as_warning: false\n",
        encoding="utf-8",
    )
    (config_dir / LEGACY_CONFIG_NAME).write_text(
        "build-validation:\n  yamllint:\n    error_as_warning: true\n",
        encoding="utf-8",
    )
    assert read_config.find_config_file() == Path("build-validation.yml")
    assert read_config.get_config_value("yamllint", "error_as_warning") is False


def test_alternate_root_key(config_dir: Path) -> None:
    """Accept global-build-validation as an alternate YAML root key."""
    (config_dir / "build-validation.yml").write_text(
        "global-build-validation:\n  prettier:\n    error_as_warning: true\n",
        encoding="utf-8",
    )
    assert read_config.get_config_value("prettier", "error_as_warning") is True


def test_gbv_config_file_env(config_dir: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """Honor GBV_CONFIG_FILE for local runs against a specific YAML file."""
    custom = config_dir / "custom.yml"
    custom.write_text(
        "build-validation:\n  python:\n    black:\n      error_as_warning: true\n",
        encoding="utf-8",
    )
    (config_dir / "build-validation.yml").write_text(
        "build-validation:\n  python:\n    black:\n      error_as_warning: false\n",
        encoding="utf-8",
    )
    monkeypatch.setenv(read_config.CONFIG_FILE_ENV, str(custom))
    assert read_config.get_config_value("python", "black", "error_as_warning") is True


def test_as_bool() -> None:
    """Coerce YAML booleans and true/false strings."""
    assert read_config.as_bool(True) is True
    assert read_config.as_bool("FALSE") is False
    assert read_config.as_bool("true") is True
    assert read_config.as_bool(None) is None


def test_legacy_config_filename_removed_from_source() -> None:
    """Fail if the retired vendor config filename is referenced again."""
    skip_parts = {".git", ".nox", "__pycache__", ".venv", ".pytest_cache"}
    hits: list[str] = []
    for path in ROOT.rglob("*"):
        if any(part in skip_parts for part in path.parts):
            continue
        if not path.is_file() or path.name.startswith("test_"):
            continue
        try:
            text = path.read_text(encoding="utf-8")
        except (UnicodeDecodeError, OSError):
            continue
        if LEGACY_CONFIG_NAME in text:
            hits.append(str(path.relative_to(ROOT)))
    assert hits == []
