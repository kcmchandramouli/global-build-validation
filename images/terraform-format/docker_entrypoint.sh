#!/usr/bin/env bash
set -e
# shellcheck disable=SC1091
. /usr/local/lib/gbv/ci_report.sh
gbv_prepare_home
gbv_load_profile

if [ -n "${1:-}" ]; then
  exec "$@"
fi

if [ -e "/tmp/terraform-format.files" ]; then
  Files="$(cat /tmp/terraform-format.files)"
  if [ -z "${Files}" ]; then
    echo "Skip check because no files are modified."
    exit 0
  fi
else
  Files="$(find . \( -path '*/__pycache__/*' -o -path './.git/*' -o -path './repos/*' -o -path './.nox*/*' -o -path './.venv*/*' \) -prune -o -name '*.tf' -print)"
fi

unformatted_count=0
for file in ${Files}; do
  echo "Checking '$file'..."
  if ! terraform fmt -check -diff "$file"; then
    unformatted_count=$((unformatted_count + 1))
  fi
done

if [ "$unformatted_count" != "0" ]; then
  configured=$(python3 /usr/local/bin/read_config.py terraform-format error_as_warning || true)
  ERROR_AS_WARNING="${configured:-${ERROR_AS_WARNING:-false}}"
  gbv_fail_or_warn "Terraform format failed" || exit 1
fi
exit 0
