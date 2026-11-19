#!/bin/bash
set -euo pipefail
region=$1
dnf -y install git nodejs22 nodejs22-npm
if ! command -v node >/dev/null; then ln -s /usr/bin/node-22 /usr/local/bin/node; fi
npm_bin=$(command -v npm-22 || command -v npm)
"$npm_bin" install --global --prefix /usr/local @openai/codex@0.168.0
sudo -iu orca python3 /opt/orca-workstation/agent/configure.py "$region"
