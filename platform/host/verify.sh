#!/bin/bash
set -euo pipefail
findmnt -M /workspace -t xfs >/dev/null
systemctl is-active orca-access tailscaled orca-server
for ((i=0; i<60; i++)); do
    if sudo -iu orca orca-host status --json >/dev/null 2>&1 && curl --silent --output /dev/null --max-time 2 http://127.0.0.1:6768/; then break; fi
    sleep 2
done
curl --silent --show-error --output /dev/null --max-time 3 http://127.0.0.1:6768/
sudo -iu orca orca-host status --json | python3 -c '
import json, sys
reply = json.load(sys.stdin)
if not reply.get("ok") or "bots.create.v1" not in reply["result"]["runtime"]["capabilities"]:
    sys.exit("Orca did not advertise bot creation to clients")
'
/opt/orca-workstation/agent/verify.sh
echo 'Workspace, Orca and agent checks passed.'
