#!/usr/bin/env python3
"""Compare an Orca project's new-chat picker with the service user's OpenCode CLI."""
import argparse
import json
import os
from pathlib import Path
import socket
import subprocess
import time
import uuid


def read_catalog(metadata, workspace):
    request = {"id": str(uuid.uuid4()), "authToken": metadata["authToken"],
               "method": "agentSession.modelCatalog",
               "params": {"agent": "opencode", "worktree": "path:" + str(workspace), "waitForListing": True}}
    endpoint = next(t["endpoint"] for t in metadata["transports"] if t["kind"] == "unix")
    with socket.socket(socket.AF_UNIX, socket.SOCK_STREAM) as connection:
        connection.settimeout(75)
        connection.connect(endpoint)
        connection.sendall((json.dumps(request) + "\n").encode())
        for line in connection.makefile():
            reply = json.loads(line)
            if reply.get("id") != request["id"]:
                continue
            if not reply.get("ok") or reply.get("_meta", {}).get("runtimeId") != metadata["runtimeId"]:
                raise RuntimeError("The selected Orca runtime could not return the workspace catalog")
            return reply["result"]
    raise RuntimeError("Orca closed the catalog request")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("workspace", type=Path, help="A registered Orca checkout on this host")
    workspace = parser.parse_args().workspace.resolve(strict=True)
    cli = subprocess.check_output(["opencode", "models"], cwd=workspace, text=True, timeout=100)
    expected = set(cli.splitlines())
    if not expected or any(not i.startswith("amazon-bedrock/") for i in expected):
        raise SystemExit("OpenCode needs a Bedrock-only catalog")
    state = Path(os.environ.get("ORCA_USER_DATA_PATH", "/workspace/orca-state"))
    metadata = json.loads((state / "orca-runtime.json").read_text())
    end = time.monotonic() + 90
    while True:
        catalog = read_catalog(metadata, workspace)
        if not catalog.get("listingInProgress") or time.monotonic() >= end:
            break
        time.sleep(1)
    actual = {item["id"] for item in catalog.get("models", [])}
    print(json.dumps({"cli": len(expected), "orca": len(actual), "missing": sorted(expected - actual),
                      "extra": sorted(actual - expected)}, indent=2))
    if actual != expected:
        raise SystemExit("Orca and OpenCode returned different model IDs")


if __name__ == "__main__":
    main()
