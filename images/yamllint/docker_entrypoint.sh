#!/usr/bin/env bash
set -e
# shellcheck disable=SC1091
. /usr/local/lib/gbv/ci_report.sh
gbv_prepare_home
gbv_load_profile

if [ -n "${1:-}" ]; then
  exec "$@"
fi

ConfigFile=/etc/yamllint/.yamllint.yaml
set +e
if [ -e "/tmp/yamllint.files" ]; then
  Files="$(cat /tmp/yamllint.files)"
  if [ -z "${Files}" ]; then
    echo "Skip check because no files are modified."
    exit 0
  fi
  # shellcheck disable=SC2086
  yamllint -c "${ConfigFile}" ${Files}
  status=$?
else
  yamllint -c "${ConfigFile}" .
  status=$?
fi
set -e

if [ "$status" != "0" ]; then
  configured=$(python3 /usr/local/bin/read_config.py yamllint error_as_warning || true)
  ERROR_AS_WARNING="${configured:-${ERROR_AS_WARNING:-false}}"
  gbv_fail_or_warn "Yamllint failed" || exit 1
fi
exit 0
