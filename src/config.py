"""Read consumer settings from build-validation.yml."""

from __future__ import annotations

import os
import pathlib
import sys
from typing import Any, Iterable, Optional, Sequence, Union

import yaml

CONFIG_FILES = ("build-validation.yml",)
ROOT_KEYS = ("build-validation", "global-build-validation")
CONFIG_FILE_ENV = "GBV_CONFIG_FILE"

PathLike = Union[str, os.PathLike[str]]


def _candidates(config_dir: Optional[PathLike] = None) -> Sequence[pathlib.Path]:
    """Return config paths to try, honoring GBV_CONFIG_FILE."""
    env = os.environ.get(CONFIG_FILE_ENV)
    if env:
        return (pathlib.Path(env),)
    base = pathlib.Path(config_dir) if config_dir is not None else pathlib.Path(".")
    return tuple(base / name for name in CONFIG_FILES)


def find_config_file(config_dir: Optional[PathLike] = None) -> Optional[pathlib.Path]:
    """Return the first existing consumer config file, if any."""
    for path in _candidates(config_dir):
        if path.is_file():
            return path
    return None


def _load_config(config_dir: Optional[PathLike] = None) -> Optional[dict[str, Any]]:
    """Load YAML from the first existing consumer config file."""
    path = find_config_file(config_dir)
    if path is None:
        return None
    with path.open(encoding="utf-8") as handle:
        data = yaml.safe_load(handle) or {}
    if isinstance(data, dict):
        return data
    return None


def get_config_value(*keys: str, config_dir: Optional[PathLike] = None) -> Any:
    """Return a nested config value or None."""
    configuration_data_root = _load_config(config_dir)
    if not configuration_data_root:
        return None

    for root_key in ROOT_KEYS:
        if root_key not in configuration_data_root:
            continue
        current: Any = configuration_data_root[root_key]
        found = True
        for key in keys:
            if isinstance(current, dict) and key in current:
                current = current[key]
            else:
                found = False
                break
        if found:
            return current
    return None


def as_bool(value: Any) -> Optional[bool]:
    """Coerce YAML and string booleans."""
    if isinstance(value, bool):
        return value
    if isinstance(value, str):
        folded = value.casefold()
        if folded == "true":
            return True
        if folded == "false":
            return False
    return None


def error_as_warning(*keys: str, default: bool = False) -> bool:
    """Return the configured failure mode, then ERROR_AS_WARNING."""
    configured = as_bool(get_config_value(*keys))
    if configured is not None:
        return configured
    env_value = os.getenv("ERROR_AS_WARNING")
    if env_value is None:
        return default
    return env_value.casefold() == "true"


def main(argv: Iterable[str]) -> int:
    """Print a nested config value for command-line use."""
    value = get_config_value(*list(argv)[1:])
    if value is not None:
        print(value)  # noqa: T201
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
