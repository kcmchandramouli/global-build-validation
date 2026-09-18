#!/usr/bin/env bash
set -e
# shellcheck disable=SC1091
. /usr/local/lib/gbv/ci_report.sh
gbv_prepare_home
gbv_load_profile

if [ -n "${1:-}" ]; then
  exec "$@"
fi

if [ -e "/tmp/markdownlint-cli2.files" ]; then
  Files="$(cat /tmp/markdownlint-cli2.files)"
  if [ -z "${Files}" ]; then
    echo "Skip check because no files are modified."
    exit 0
  fi
else
  Files="**/*.md"
fi

if [ "$(echo "${TF_BUILD:-}" | tr '[:upper:]' '[:lower:]')" = "true" ]; then
  echo "##[group]Dump npm versions"
  npm list --global --all || true
  echo "##[endgroup]"
fi

set +e
# shellcheck disable=SC2086
markdownlint-cli2-config /etc/markdownlint-cli2/.markdownlint-cli2.yaml ${Files}
status=$?
set -e

if [ "$status" != "0" ]; then
  configured=$(python3 /usr/local/bin/read_config.py markdownlint error_as_warning || true)
  ERROR_AS_WARNING="${configured:-${ERROR_AS_WARNING:-false}}"
  gbv_fail_or_warn "Markdownlint failed" || exit 1
fi
exit 0
