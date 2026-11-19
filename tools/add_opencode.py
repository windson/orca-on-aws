"""Add the OpenCode Bedrock module to an existing running Orca EC2 workstation."""
import argparse
import base64
import json
from pathlib import Path
import re
import shlex
import subprocess
import time

MODULE = Path(__file__).resolve().parents[1] / "agents/opencode-bedrock"


def policy_document(manifest, role_arn, region):
    _, partition, _, _, account, _ = role_arn.split(":", 5)
    variables = {"AWS::Partition": partition, "AWS::AccountId": account, "OpenCodeRegion": region}

    def resolve(item):
        if isinstance(item, list):
            return [resolve(value) for value in item]
        if isinstance(item, dict):
            if set(item) == {"Fn::Sub"}:
                return re.sub(r"\$\{([^}]+)\}", lambda m: variables[m[1]], item["Fn::Sub"])
            return {key: resolve(value) for key, value in item.items()}
        return item

    return resolve(manifest["policies"][0]["PolicyDocument"])


def host_command(manifest, region):
    commands = ["#!/bin/bash", "set -euo pipefail", "systemctl is-active --quiet orca-server",
                "mountpoint -q /workspace", "exec 8>/run/lock/orca-opencode-addon.lock", "flock 8",
                "ORCA_RUN_USER=$(systemctl show -p User --value orca-server)",
                '[[ -n "$ORCA_RUN_USER" && "$ORCA_RUN_USER" != root ]]', "export ORCA_RUN_USER",
                "dir=/opt/orca-workstation/addons/opencode-bedrock", 'install -d -m 0755 "$dir"']
    for name in manifest["files"]:
        if not re.fullmatch(r"[a-z]+\.(sh|py|json)", name):
            raise ValueError("Unexpected module filename")
        encoded = base64.b64encode((MODULE / name).read_bytes()).decode()
        commands.extend([f"printf %s {encoded} | base64 -d > \"$dir/{name}.new\"",
                         f'chmod 0755 "$dir/{name}.new"', f'mv -f "$dir/{name}.new" "$dir/{name}"'])
    commands.extend([f'"$dir/install.sh" {shlex.quote(region)}', '"$dir/activate.sh"', '"$dir/verify.sh"'])
    return "\n".join(commands)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--instance-id", required=True)
    parser.add_argument("--profile", default="default")
    parser.add_argument("--region", default="us-east-1", help="EC2 region")
    parser.add_argument("--bedrock-region", help="Defaults to the EC2 region")
    parser.add_argument("--plan", action="store_true")
    args = parser.parse_args()
    region = args.bedrock_region or args.region
    if not re.fullmatch(r"[a-z]{2}(?:-[a-z0-9]+)+-\d+", region):
        parser.error("Invalid Bedrock region")
    cli = ["aws", "--profile", args.profile, "--region", args.region, "--no-cli-pager", "--output", "json"]

    def aws(*command):
        result = subprocess.run([*cli, *command], text=True, capture_output=True)
        if result.returncode:
            raise RuntimeError(result.stderr.strip())
        return json.loads(result.stdout) if result.stdout.strip() else {}

    host = aws("ec2", "describe-instances", "--instance-ids", args.instance_id)["Reservations"][0]["Instances"][0]
    if host["State"]["Name"] != "running" or host["Architecture"] != "x86_64":
        parser.error("Expected a running x86_64 workstation")
    profile = host["IamInstanceProfile"]["Arn"].rsplit("/", 1)[1]
    role, = aws("iam", "get-instance-profile", "--instance-profile-name", profile)["InstanceProfile"]["Roles"]
    manifest = json.loads((MODULE / "agent.json").read_text())
    desired = policy_document(manifest, role["Arn"], region)
    name = manifest["policies"][0]["PolicyName"]
    policy_args = ["--role-name", role["RoleName"], "--policy-name", name]
    names = aws("iam", "list-role-policies", "--role-name", role["RoleName"])["PolicyNames"]
    if name in names and aws("iam", "get-role-policy", *policy_args)["PolicyDocument"] != desired:
        parser.error("An existing policy with this name differs. Review it before changing inference access.")
    print(f"OpenCode will use Bedrock in {region}. Dedicated role policy: {name}.", flush=True)
    if args.plan:
        print(json.dumps(desired, indent=2))
        return

    command = host_command(manifest, region)
    command_id = aws("ssm", "send-command", "--document-name", "AWS-RunShellScript",
                     "--instance-ids", args.instance_id, "--parameters",
                     json.dumps({"commands": [command], "executionTimeout": ["600"]}),
                     "--comment", "Install OpenCode beside the existing Orca agents")["Command"]["CommandId"]
    print(f"SSM installation command {command_id}", flush=True)
    deadline = time.monotonic() + 720
    while time.monotonic() < deadline:
        time.sleep(4)
        try:
            result = aws("ssm", "get-command-invocation", "--command-id", command_id,
                         "--instance-id", args.instance_id)
        except RuntimeError as error:
            if "InvocationDoesNotExist" in str(error):
                continue
            raise
        if result["Status"] in ("Pending", "InProgress", "Delayed", "Cancelling"):
            continue
        print(result.get("StandardOutputContent", ""))
        if result["Status"] != "Success":
            raise SystemExit(result.get("StandardErrorContent") or result["Status"])
        break
    else:
        raise SystemExit(f"Check SSM command {command_id} before retrying")
    if name not in names:
        aws("iam", "put-role-policy", *policy_args, "--policy-document", json.dumps(desired))
    if aws("iam", "get-role-policy", *policy_args)["PolicyDocument"] != desired:
        raise RuntimeError("Installed policy differs from the module")
    print("OpenCode installed. Run the inference and Orca checks in the module guide.")


if __name__ == "__main__":
    main()
