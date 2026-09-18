#!/usr/bin/env bash
set -e
# shellcheck disable=SC1091
. /usr/local/lib/gbv/ci_report.sh
gbv_prepare_home
gbv_load_profile
exec "$@"
