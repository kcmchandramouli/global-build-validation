"""Local-path helpers for python-validation (no Docker required)."""

from __future__ import annotations

from pathlib import Path

PYTHON_VALIDATION = Path(__file__).resolve().parents[1] / "images" / "python-validation"
NOXFILE = PYTHON_VALIDATION / "noxfile.py"


def test_tool_config_files_exist_in_checkout() -> None:
    """Checker configs must be resolvable without the container path."""
    assert (PYTHON_VALIDATION / "flake8.ini").is_file()
    assert (PYTHON_VALIDATION / "pyproject.toml").is_file()
    assert (PYTHON_VALIDATION / "pylint.rc").is_file()
    assert (PYTHON_VALIDATION / "pytest-coverage.rc").is_file()


def test_noxfile_uses_local_config_fallback() -> None:
    """Python sessions should not hard-code image-only config paths."""
    text = NOXFILE.read_text(encoding="utf-8")
    assert "def tool_config_dir" in text
    assert '"/etc/python-validation/flake8.ini"' not in text
    assert '"/etc/python-validation/pyproject.toml"' not in text
    assert '"/etc/python-validation/pylint.rc"' not in text
    assert "--cov-config=/etc/python-validation/pytest-coverage.rc" not in text
