#!/usr/bin/env bash
set -e
# shellcheck disable=SC1091
. /usr/local/lib/gbv/ci_report.sh

DEFAULT_REGEX='^(main|master|develop|(feature|feat|fix|hotfix|release|chore)/[A-Za-z0-9._-]+)$'
BranchToCheck=$(echo "${BRANCH_TO_CHECK:-}" | sed 's|refs/heads/||; s|refs/pull/||')
BranchRegularExpression=$(python3 /usr/local/bin/read_config.py branch-name-validation branch_regex || true)

if [ -z "${BranchRegularExpression}" ]; then
  BranchRegularExpression="${BRANCH_NAME_REGULAR_EXPRESSION:-$DEFAULT_REGEX}"
else
  echo "Using regular expression from build-validation.yml"
fi

if echo "${BranchToCheck}" | grep -Eq "$BranchRegularExpression"; then
  echo "Branch name [${BranchToCheck}] follows regular expression >>${BranchRegularExpression}<<"
  exit 0
fi

configured=$(python3 /usr/local/bin/read_config.py branch-name-validation error_as_warning || true)
ERROR_AS_WARNING="${configured:-${ERROR_AS_WARNING:-false}}"
gbv_fail_or_warn "Branch name [${BranchToCheck}] does not follow regular expression >>${BranchRegularExpression}<<" || exit 1
exit 0
