#!/usr/bin/env bash
set -e
# shellcheck disable=SC1091
. /usr/local/lib/gbv/ci_report.sh
gbv_prepare_home
gbv_load_profile

if [ -z "${1:-}" ]; then
  python3 /etc/unreferenced-image-check/check_unreferenced_image.py
  exit $?
fi

exec "$@"
