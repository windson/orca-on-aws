#!/bin/bash
set -euo pipefail
# Orca discovers the system CLI on PATH. The owner signs in from a remote terminal.
test -x /usr/bin/kiro-cli
