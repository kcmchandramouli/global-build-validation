"""YAML formatting on top of yamlfix.

yamlfix turns the last literal block into ``|-`` when nothing follows it.
This check puts ``|`` back and keeps one empty line between workflow jobs.
"""

from __future__ import annotations

import re
import sys
from pathlib import Path

from yamlfix.config import configure_yamlfix
from yamlfix.model import YamlfixConfig
from yamlfix.services import fix_code

from src.output import error, info

_BLOCK = re.compile(r"^.*:\s+(\|[-+]?)(?:\s+#.*)?$")
_JOB_KEY = re.compile(r"^  [A-Za-z_][A-Za-z0-9_-]*:$")


def format_yaml(source: str, config: YamlfixConfig) -> str:
    """Format YAML, keep a trailing ``|`` block, and separate workflow jobs."""
    fixed = fix_code(source, config)
    restored = _restore_keep_style(source, fixed)
    return _separate_jobs(restored)


def check_files(config_path: str, files: list[str]) -> int:
    """Return 0 when every file already matches format_yaml."""
    config = YamlfixConfig()
    configure_yamlfix(config, [config_path])
    changed: list[str] = []
    for file_name in files:
        source = Path(file_name).read_text(encoding="utf-8")
        if format_yaml(source, config) != source:
            changed.append(file_name)
            info(f"Would fix {file_name}")
    if changed:
        return 1
    info(f"Checked {len(files)} files: 0 fixed, {len(files)} left unchanged")
    return 0


def _restore_keep_style(source: str, fixed: str) -> str:
    """Put ``|`` back where yamlfix rewrote the last block as ``|-``."""
    styles = _block_styles(source)
    lines = fixed.splitlines()
    indexes = [index for index, line in enumerate(lines) if _BLOCK.match(line)]
    if len(styles) != len(indexes):
        return _with_final_newline("\n".join(lines))
    for style, index in zip(styles, indexes):
        match = _BLOCK.match(lines[index])
        if match and style == "|" and match.group(1) == "|-":
            start, end = match.span(1)
            lines[index] = lines[index][:start] + "|" + lines[index][end:]
    return _with_final_newline("\n".join(lines))


def _block_styles(source: str) -> list[str]:
    return [
        match.group(1) for line in source.splitlines() if (match := _BLOCK.match(line))
    ]


def _separate_jobs(text: str) -> str:
    """One empty line between jobs, and nothing after the last job."""
    lines = ["" if not line.strip() else line for line in text.splitlines()]
    span = _jobs_span(lines)
    if span is None:
        return _with_final_newline("\n".join(lines))
    start, end = span
    body = _gap_before_jobs(lines[start + 1 : end])
    return _with_final_newline("\n".join(lines[: start + 1] + body + lines[end:]))


def _jobs_span(lines: list[str]) -> tuple[int, int] | None:
    try:
        start = lines.index("jobs:")
    except ValueError:
        return None
    end = len(lines)
    for index in range(start + 1, len(lines)):
        line = lines[index]
        if line and not line.startswith((" ", "#")):
            end = index
            break
    return start, end


def _gap_before_jobs(body: list[str]) -> list[str]:
    rebuilt: list[str] = []
    seen_job = False
    pending: list[str] = []
    for line in body:
        if _JOB_KEY.match(line):
            if seen_job:
                rebuilt.append("")
            seen_job = True
            pending = []
            rebuilt.append(line)
            continue
        if line == "":
            pending.append(line)
            continue
        rebuilt.extend(pending)
        pending = []
        rebuilt.append(line)
    return rebuilt


def _with_final_newline(text: str) -> str:
    stripped = text.rstrip("\n")
    if not stripped:
        return ""
    return stripped + "\n"


def main(argv: list[str]) -> int:
    """Check files passed after the yamlfix config path."""
    if len(argv) < 3:
        error("usage: python -m src.checks.yaml_format CONFIG FILE...")
        return 2
    return check_files(argv[1], argv[2:])


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
