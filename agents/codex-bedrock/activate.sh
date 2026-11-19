#!/bin/bash
set -euo pipefail
sudo -iu orca orca-host account select --agent codex --account system --json >/dev/null
sudo -iu orca python3 /opt/orca-workstation/agent/activate.py
