"""HTTP checks for links found in Markdown files."""

from __future__ import annotations

import json
import os
import re
import sys
import time
from pathlib import Path
from typing import Any, Optional
from urllib.parse import urlparse

import requests

_FENCE = re.compile(r"```.*?```", re.DOTALL)
_INLINE = re.compile(r"(?<!!)\[(?:\\.|[^\[\]\\])*\]\(\s*<?([^)\s>]+)>?")
_ANGLE = re.compile(r"<(https?://[^>\s]+)>")
_REFERENCE = re.compile(r"(?m)^[ ]{0,3}\[[^\]]+\]:[ \t]+<?([^>\s]+)>?")
_USER_AGENT = "global-build-validation"


def extract_links(text: str) -> list[str]:
    """Return Markdown link targets, skipping fenced code blocks."""
    stripped = _FENCE.sub("", text)
    found: list[str] = []
    for pattern in (_INLINE, _ANGLE, _REFERENCE):
        found.extend(pattern.findall(stripped))
    return found


def _seconds(value: Any, default: float) -> float:
    """Parse a timeout or delay such as ``10s`` or ``500ms``."""
    if value is None:
        return default
    if isinstance(value, (int, float)):
        return float(value)
    text = str(value).strip().casefold()
    if text.endswith("ms"):
        return float(text[:-2]) / 1000
    if text.endswith("s"):
        return float(text[:-1])
    return float(text)


def _ignored(url: str, patterns: list[re.Pattern[str]]) -> bool:
    """Return True when a configured ignore pattern matches the URL."""
    return any(pattern.search(url) for pattern in patterns)


def _apply_replacements(url: str, config: dict[str, Any]) -> str:
    """Apply replacement patterns, expanding {{BASEURL}} from the environment."""
    base = os.environ.get("BASEURL", "")
    current = url
    for item in config.get("replacementPatterns") or []:
        pattern = item.get("pattern")
        replacement = item.get("replacement")
        if not isinstance(pattern, str) or not isinstance(replacement, str):
            continue
        current = re.sub(pattern, replacement.replace("{{BASEURL}}", base), current)
    return current


def _headers(url: str, config: dict[str, Any]) -> dict[str, str]:
    """Return request headers, including auth when the URL matches."""
    headers = {"User-Agent": _USER_AGENT}
    for item in config.get("httpHeaders") or []:
        prefixes = item.get("urls") or []
        if not any(
            isinstance(prefix, str) and url.startswith(prefix) for prefix in prefixes
        ):
            continue
        for key, value in (item.get("headers") or {}).items():
            if isinstance(key, str) and isinstance(value, str) and value:
                headers[key] = value
    return headers


def _compile_ignores(config: dict[str, Any]) -> list[re.Pattern[str]]:
    """Compile ignorePatterns from the link-check config."""
    compiled: list[re.Pattern[str]] = []
    for item in config.get("ignorePatterns") or []:
        pattern = item.get("pattern") if isinstance(item, dict) else None
        if isinstance(pattern, str):
            compiled.append(re.compile(pattern))
    return compiled


def _alive_codes(config: dict[str, Any]) -> set[int]:
    """Return HTTP status codes that count as a live link."""
    codes = config.get("aliveStatusCodes") or [200]
    return {int(code) for code in codes}


def _retry_delay(response: requests.Response, fallback: float) -> float:
    """Return how long to wait after HTTP 429."""
    header = response.headers.get("Retry-After")
    if header and header.isdigit():
        return float(header)
    return fallback


def check_url(
    url: str, config: dict[str, Any], session: requests.Session
) -> Optional[str]:
    """Return an error message when the URL is not alive."""
    timeout = _seconds(config.get("timeout"), 10)
    retries = int(config.get("retryCount") or 0)
    retry_on_429 = bool(config.get("retryOn429"))
    fallback = _seconds(config.get("fallbackRetryDelay"), 10)
    alive = _alive_codes(config)
    attempt = 0
    while True:
        try:
            response = session.get(
                url,
                headers=_headers(url, config),
                timeout=timeout,
                allow_redirects=True,
            )
        except requests.RequestException as exc:
            return f"{url} -> {exc.__class__.__name__}: {exc}"
        if response.status_code == 429 and retry_on_429 and attempt < retries:
            time.sleep(_retry_delay(response, fallback))
            attempt += 1
            continue
        if response.status_code not in alive:
            return f"{url} -> HTTP {response.status_code}"
        return None


def check_files(paths: list[str], config: dict[str, Any]) -> list[str]:
    """Check unique HTTP(S) links in the given Markdown files."""
    ignores = _compile_ignores(config)
    errors: list[str] = []
    seen: set[str] = set()
    with requests.Session() as session:
        for path in paths:
            text = Path(path).read_text(encoding="utf-8")
            for raw in extract_links(text):
                replaced = _apply_replacements(raw, config)
                if _ignored(raw, ignores) or _ignored(replaced, ignores):
                    continue
                parsed = urlparse(replaced)
                if parsed.scheme not in {"http", "https"} or replaced in seen:
                    continue
                seen.add(replaced)
                message = check_url(replaced, config, session)
                if message:
                    errors.append(f"{path}: {message}")
    return errors


def main(argv: list[str] | None = None) -> int:
    """Check links. Arguments are a config path followed by Markdown files."""
    args = list(sys.argv[1:] if argv is None else argv)
    if len(args) < 2:
        print(  # noqa: T201
            "usage: python -m src.checks.links CONFIG.json FILE.md ...",
            file=sys.stderr,
        )
        return 2
    config_path, *files = args
    config = json.loads(Path(config_path).read_text(encoding="utf-8"))
    if not isinstance(config, dict):
        print(  # noqa: T201
            "markdown-link-check configuration must be a JSON object",
            file=sys.stderr,
        )
        return 2
    errors = check_files(files, config)
    for line in errors:
        print(line, file=sys.stderr)  # noqa: T201
    return 1 if errors else 0


if __name__ == "__main__":
    sys.exit(main())
