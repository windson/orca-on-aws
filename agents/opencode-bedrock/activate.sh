#!/bin/bash
set -euo pipefail
# Orca detects the opencode executable on PATH for native chat and terminal launches.
# The system CLI account uses the instance role; no interactive login is needed.
test -x /usr/local/bin/opencode
