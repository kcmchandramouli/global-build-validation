#!/usr/bin/env bash
# Azure Pipelines agent entrypoint for optional KEDA ScaledJobs.
# See https://keda.sh/docs/2.10/scalers/azure-pipelines/#configuring-the-agent-container

set -e

AZP_AGENT_DIR="${AZP_AGENT_DIR:-/opt/az_agent}"
cd "$AZP_AGENT_DIR"

if [ -z "$AZP_URL" ]; then
  echo 1>&2 "error: missing AZP_URL environment variable"
  exit 1
fi

if [ -z "$AZP_TOKEN_FILE" ]; then
  if [ -z "$AZP_TOKEN" ]; then
    echo 1>&2 "error: missing AZP_TOKEN environment variable"
    exit 1
  fi
  AZP_TOKEN_FILE=/tmp/.token
  echo -n "$AZP_TOKEN" >"$AZP_TOKEN_FILE"
fi

unset AZP_TOKEN

if [ -z "$AZP_POOL" ]; then
  echo 1>&2 "error: missing AZP_POOL environment variable"
  exit 1
fi

AZP_WORK=/tmp/az_agent_work
mkdir -p "$AZP_WORK"
chmod 0777 "$AZP_WORK"

cleanup() {
  if [ -e config.sh ]; then
    print_header "Cleanup. Removing Azure Pipelines agent..."
    while true; do
      ./config.sh remove --unattended --auth PAT --token "$(cat "$AZP_TOKEN_FILE")" && break
      echo "Retrying in 30 seconds..."
      sleep 30
    done
  fi
}

print_header() {
  light_cyan='\033[1;36m'
  nocolor='\033[0m'
  echo -e "${light_cyan}$1${nocolor}"
}

export VSO_AGENT_IGNORE=AZP_TOKEN,AZP_TOKEN_FILE

print_header "1. Use Azure Pipelines agent at $PWD..."
# shellcheck disable=SC1091
. ./env.sh

trap 'cleanup; exit 0' EXIT
trap 'cleanup; exit 130' INT
trap 'cleanup; exit 143' TERM

print_header "2. Configuring Azure Pipelines agent..."
./config.sh --unattended \
  --agent "${AZP_AGENT_NAME:-$(hostname)}" \
  --url "$AZP_URL" \
  --auth PAT \
  --token "$(cat "$AZP_TOKEN_FILE")" \
  --pool "${AZP_POOL}" \
  --work "${AZP_WORK}" \
  --replace \
  --acceptTeeEula &
wait $!

print_header "3. Running Azure Pipelines agent..."
./run-docker.sh "$@" --once &
wait $!
