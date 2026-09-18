#!/usr/bin/env bash
set -e
# shellcheck disable=SC1091
. /usr/local/lib/gbv/ci_report.sh
gbv_prepare_home
gbv_load_profile

if [ -n "${1:-}" ]; then
  exec "$@"
fi

if [ "$(echo "${TF_BUILD:-}" | tr '[:upper:]' '[:lower:]')" = "true" ]; then
  echo "##[group]Dump npm versions"
  npm list --global --all || true
  echo "##[endgroup]"
fi

python3 /etc/markdown-link-check/update_config.py

set +e
find . \( -path '*/__pycache__/*' -o -path './.git/*' -o -path './repos/*' -o -path './.nox*/*' -o -path './.venv*/*' -o -path './.pytest_cache/*' \) -prune -o -name '*.md' -print0 \
  | xargs -0 -r -n1 markdown-link-check --verbose --config /tmp/markdown-link-check.json
status=$?
set -e

if [ "$status" != "0" ]; then
  configured=$(python3 /usr/local/bin/read_config.py markdown-link-check error_as_warning || true)
  ERROR_AS_WARNING="${configured:-${ERROR_AS_WARNING:-false}}"
  gbv_fail_or_warn "Markdown link check failed" || exit 1
fi
exit 0
