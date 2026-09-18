#!/usr/bin/env bash
set -euo pipefail

export DEBIAN_FRONTEND=noninteractive
AZP_AGENT_VERSION="${AZP_AGENT_VERSION:-3.248.0}"
AZP_AGENT_DIR="${AZP_AGENT_DIR:-/opt/az_agent}"
INSTALL_AZP_AGENT="${INSTALL_AZP_AGENT:-true}"

apt-get update
apt-get install -y --no-install-recommends \
  ca-certificates \
  curl \
  git \
  gnupg \
  jq \
  python3 \
  python3-pip \
  python3-venv \
  python3-yaml \
  unzip

if [ "$INSTALL_AZP_AGENT" = "true" ]; then
  mkdir -p "$AZP_AGENT_DIR"
  curl -fsSL -o /tmp/azp-agent.tar.gz \
    "https://vstsagentpackage.azureedge.net/agent/${AZP_AGENT_VERSION}/vsts-agent-linux-x64-${AZP_AGENT_VERSION}.tar.gz"
  tar -xzf /tmp/azp-agent.tar.gz -C "$AZP_AGENT_DIR"
  rm /tmp/azp-agent.tar.gz
  "$AZP_AGENT_DIR/bin/installdependencies.sh"
  chmod -R 0755 "$AZP_AGENT_DIR"
fi

rm -rf /var/lib/apt/lists/*
mkdir -p /workspace /usr/local/lib/gbv
chmod +x /usr/local/bin/read_config.py /usr/local/bin/az_agent.sh
