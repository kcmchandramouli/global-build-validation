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
checkov --directory . --framework terraform --skip-path repos --skip-download
status=$?
set -e

if [ "$status" != "0" ]; then
  configured=$(python3 /usr/local/bin/read_config.py terraform-validation error_as_warning || true)
  ERROR_AS_WARNING="${configured:-${ERROR_AS_WARNING:-false}}"
  gbv_fail_or_warn "Terraform validation failed" || exit 1
fi
exit 0
