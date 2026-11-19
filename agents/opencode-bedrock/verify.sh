#!/bin/bash
set -euo pipefail
user=${ORCA_RUN_USER:-orca}
sudo -Hu "$user" -- /usr/local/bin/opencode --version
sudo -Hu "$user" -- python3 - "$@" <<'PY'
import argparse
import json
from pathlib import Path
import subprocess
import tempfile

parser = argparse.ArgumentParser()
parser.add_argument("--inference", nargs="?", const="amazon-bedrock/openai.gpt-oss-20b-1:0")
args = parser.parse_args()
with tempfile.TemporaryDirectory() as project:
    # Verify a normal project cannot enable a second inference provider.
    Path(project, "opencode.json").write_text(json.dumps({"enabled_providers": ["amazon-bedrock", "opencode"]}))
    def run(*args):
        return subprocess.check_output(["/usr/local/bin/opencode", *args], cwd=project, text=True, timeout=150)
    models = set(run("models").splitlines())
    bedrock = set(run("models", "amazon-bedrock").splitlines())
    if models != bedrock or "amazon-bedrock/openai.gpt-oss-20b-1:0" not in bedrock:
        raise SystemExit("Set enabled_providers to only amazon-bedrock in /etc/opencode/opencode.jsonc")
    print(f"OpenCode lists {len(bedrock)} models, all through Bedrock")
    if args.inference:
        if args.inference not in bedrock:
            raise SystemExit("Select a model from the Bedrock picker")
        output = run("run", "--format", "json", "-m", args.inference, "Reply exactly ORCA_OPENCODE_OK. Use no tools.")
        events = [json.loads(line) for line in output.splitlines() if line.strip()]
        if any(e.get("type") == "error" for e in events):
            raise SystemExit("OpenCode reported a provider error")
        if not any(e.get("type") == "text" and e["part"]["text"].strip() == "ORCA_OPENCODE_OK" for e in events):
            raise SystemExit("Expected model reply was absent")
        print("OpenCode inference passed", args.inference)
PY
