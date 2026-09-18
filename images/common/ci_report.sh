#!/usr/bin/env bash
# Shared CI reporting for Azure Pipelines and GitHub Actions.

gbv_error_as_warning() {
  echo "${ERROR_AS_WARNING:-false}" | tr '[:upper:]' '[:lower:]'
}

gbv_fail_or_warn() {
  local message="$1"
  if [ "$(gbv_error_as_warning)" = "true" ]; then
    echo "::warning::$message (warn only)"
    echo "##vso[task.logissue type=warning]$message (warn only)"
    echo "##vso[task.complete result=SucceededWithIssues]"
    return 0
  fi
  echo "::error::$message"
  echo "##vso[task.logissue type=error]$message"
  echo "##vso[task.complete result=Failed]"
  return 1
}

gbv_prepare_home() {
  export HOME="/home/$(whoami 2>/dev/null)"
  if [ ! -d "${HOME}" ] || [ "$HOME" = "/home/" ]; then
    export HOME="${DOCKER_WORKDIR:-/workspace}"
  fi
}

gbv_load_profile() {
  if [ -d /etc/profile.d ]; then
    for i in /etc/profile.d/*.sh; do
      if [ -r "$i" ]; then
        # shellcheck disable=SC1090
        . "$i"
      fi
    done
    unset i
  fi
}
