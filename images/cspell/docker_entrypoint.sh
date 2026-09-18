#!/usr/bin/env bash
set -e
# shellcheck disable=SC1091
. /usr/local/lib/gbv/ci_report.sh
gbv_prepare_home
gbv_load_profile

if [ -n "${1:-}" ]; then
  exec "$@"
fi

GlobingPatterns='**'
if [ -e "/tmp/cspell.files" ]; then
  GlobingPatterns="$(cat /tmp/cspell.files)"
  if [ -z "${GlobingPatterns}" ]; then
    echo "Skip check because no files are modified."
    exit 0
  fi
fi

if [ "$(echo "${TF_BUILD:-}" | tr '[:upper:]' '[:lower:]')" = "true" ]; then
  echo "##[group]Dump npm versions"
  npm list --global --all || true
  echo "##[endgroup]"
fi

CspellConfig=/tmp/cspell.yml
DefaultConfig=/etc/cspell/cspell.json
{
  echo "import:"
  echo "  - ${DefaultConfig}"
  if [ -n "${CSPELL_CONFIG_FILE:-}" ]; then
    echo "  - ${CSPELL_CONFIG_FILE}"
  fi
  if [ -n "${CSPELL_CONFIG_CONTENT_JSON:-}" ]; then
    echo "${CSPELL_CONFIG_CONTENT_JSON}" >/tmp/cspell.pipeline.json
    echo "  - /tmp/cspell.pipeline.json"
  fi
} >"${CspellConfig}"

LocalConfig=$(ls *cspell.* 2>/dev/null || true)
if [ -n "${LocalConfig}" ]; then
  echo "  - ${LocalConfig}" >>"${CspellConfig}"
fi

echo "CSpell configuration file is:"
cat "${CspellConfig}"

set +e
# shellcheck disable=SC2086
cspell lint --show-suggestions --color --no-must-find-files --config "${CspellConfig}" ${GlobingPatterns}
status=$?
set -e

if [ "$status" != "0" ]; then
  if [ -z "$(ls cspell.* 2>/dev/null || true)" ]; then
    ERROR_AS_WARNING=true gbv_fail_or_warn "CSpell check failed"
  else
    gbv_fail_or_warn "CSpell check failed" || exit 1
  fi
fi
exit 0
