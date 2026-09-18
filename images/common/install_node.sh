#!/usr/bin/env bash
# Install Node.js 18 from NodeSource.

set -euo pipefail
curl -fsSL https://deb.nodesource.com/setup_18.x | bash -
apt-get install -y --no-install-recommends nodejs
rm -rf /var/lib/apt/lists/*
