#!/usr/bin/env bash
set -e
# shellcheck disable=SC1091
. /usr/local/lib/gbv/ci_report.sh
gbv_prepare_home
gbv_load_profile

if [ -z "${1:-}" ] || [ "${1#-}" != "${1}" ]; then
  if [ "$(echo "${TF_BUILD:-}" | tr '[:upper:]' '[:lower:]')" = "true" ]; then
    echo "##[group]Dump python packages"
    python3 -m pip freeze
    echo "##[endgroup]"
  fi
  export DOCKER_ENTRYPOINT="${DOCKER_ENTRYPOINT:-nox --noxfile /etc/python-validation/noxfile.py --no-venv --non-interactive --forcecolor}"
  # shellcheck disable=SC2086
  set -- $DOCKER_ENTRYPOINT "$@"
fi

exec "$@"
