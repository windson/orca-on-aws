#!/bin/bash
set -euo pipefail
user=${ORCA_RUN_USER:-orca}
cli=/opt/orca-server/bin/orca-ide
sudo -Hu "$user" /usr/bin/kiro-cli --version
sudo -Hu "$user" /usr/bin/kiro-cli acp --help >/dev/null
sudo -Hu "$user" env ORCA_USER_DATA_PATH=/workspace/orca-state "$cli" agent installed --json |
    python3 -c '
import json, sys
reply = json.load(sys.stdin)
if not reply.get("ok") or not any(a["id"] == "kiro" for a in reply["result"]["agents"]):
    sys.exit("Orca could not discover Kiro. Check the host agent settings and PATH.")
print("Orca detects Kiro")
'
