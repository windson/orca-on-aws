#!/usr/bin/python3
"""Set a newly created Orca profile to use Codex's own permission settings."""
import json
from pathlib import Path
import socket
import uuid

meta = json.loads(Path("/workspace/orca-state/orca-runtime.json").read_text())
endpoint = next(t["endpoint"] for t in meta["transports"] if t["kind"] == "unix")
request = {"id": str(uuid.uuid4()), "authToken": meta["authToken"],
           "method": "settings.mutateAgentLaunch",
           "params": {"type": "permission", "agent": "codex", "choice": "own"}}
with socket.socket(socket.AF_UNIX, socket.SOCK_STREAM) as client:
    client.settimeout(30)
    client.connect(endpoint)
    client.sendall((json.dumps(request) + "\n").encode())
    for line in client.makefile():
        reply = json.loads(line)
        if reply.get("id") == request["id"]:
            if (reply.get("ok") and reply.get("_meta", {}).get("runtimeId") == meta["runtimeId"]
                    and reply["result"]["settings"]["agentPermission"]["overrides"].get("codex") == "own"):
                break
            raise RuntimeError("Orca could not confirm the Codex permission selection")
    else:
        raise RuntimeError("Orca closed the owner connection before confirming the setting")
