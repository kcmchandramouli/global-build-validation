#!/usr/bin/env bash
set -e
# shellcheck disable=SC1091
. /usr/local/lib/gbv/ci_report.sh
gbv_prepare_home
gbv_load_profile

if [ -n "${1:-}" ]; then
  exec "$@"
fi

set +e
if [ -e "/tmp/prettier-check.files" ]; then
  Files="$(cat /tmp/prettier-check.files)"
  if [ -z "${Files}" ]; then
    echo "Skip check because no files are modified."
    exit 0
  fi
  # shellcheck disable=SC2086
  prettier --no-editorconfig --config /etc/prettier-check/.prettierrc --check ${Files}
  status=$?
else
  prettier --no-editorconfig --config /etc/prettier-check/.prettierrc --check --no-error-on-unmatched-pattern \
    "**/*.md" "**/*.yaml" "**/*.yml" "**/*.toml"
  status=$?
fi
set -e

if [ "$status" != "0" ]; then
  configured=$(python3 /usr/local/bin/read_config.py prettier error_as_warning || true)
  ERROR_AS_WARNING="${configured:-${ERROR_AS_WARNING:-false}}"
  gbv_fail_or_warn "Prettier check failed" || exit 1
fi
exit 0
