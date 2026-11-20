"""Create a fresh Orca workstation from this checkout using the AWS CLI."""
import argparse
import json
import re
import subprocess
import tempfile
from pathlib import Path

from render import supported_agents, template

AMI_PARAMETER = "/aws/service/ami-amazon-linux-latest/al2023-ami-kernel-6.1-x86_64"


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--stack", required=True, help="A new CloudFormation stack name")
    parser.add_argument("--region", default="us-east-1")
    parser.add_argument("--profile", default="default")
    parser.add_argument("--agent", choices=supported_agents(), default="codex-bedrock")
    parser.add_argument("--instance-type", default="g5.2xlarge", choices=["t3.medium", "t3.large", "g5.2xlarge"],
                        help="New host size (default: g5.2xlarge with an NVIDIA A10G; t3.large is CPU-only)")
    parser.add_argument("--az", help="Use a specific offered Availability Zone")
    parser.add_argument("--ami-id", help="Pin a compatible x86_64 Amazon Linux 2023 Nitro AMI")
    parser.add_argument("--root-gib", type=int, default=30)
    parser.add_argument("--workspace-gib", type=int, default=150)
    parser.add_argument("--snapshot", help="Restore a workspace snapshot from this reference layout")
    parser.add_argument("--parameter", action="append", default=[], metavar="KEY=VALUE",
                        help="Override an agent parameter, e.g. BedrockRegion=us-east-1")
    parser.add_argument("--plan", action="store_true", help="Resolve values and validate with AWS without creating resources")
    args = parser.parse_args()
    if not re.fullmatch("[A-Za-z][A-Za-z0-9-]{0,127}", args.stack):
        parser.error("Invalid CloudFormation stack name")
    base = template(args.agent)
    manifest_path = Path(__file__).resolve().parents[1] / "agents" / args.agent / "agent.json"
    module = json.loads(manifest_path.read_text())
    overrides = {}
    for item in args.parameter:
        key, sep, value = item.partition("=")
        if not sep or key not in module["parameters"]:
            parser.error(f"Expected an agent parameter from {list(module['parameters'])}")
        overrides[key] = value
    if not 16 <= args.root_gib <= 16384 or not 30 <= args.workspace_gib <= 65536:
        parser.error("Disk size outside template bounds")

    cli = ["aws", "--profile", args.profile, "--region", args.region, "--no-cli-pager"]
    def aws(*command):
        return subprocess.check_output([*cli, *command, "--output", "text"], text=True).strip()

    zones = sorted(aws("ec2", "describe-instance-type-offerings", "--location-type", "availability-zone",
                       "--filters", "Name=instance-type,Values=" + args.instance_type,
                       "--query", "InstanceTypeOfferings[].Location").split())
    if not zones or (args.az and args.az not in zones):
        parser.error(f"{args.instance_type} is unavailable in the requested location. Offered AZs: {zones}")
    az = args.az or zones[0]
    ami = args.ami_id or aws("ssm", "get-parameter", "--name", AMI_PARAMETER, "--query", "Parameter.Value")
    if args.snapshot:
        info = aws("ec2", "describe-snapshots", "--snapshot-ids", args.snapshot,
                   "--query", "Snapshots[0].[State,VolumeSize]").split()
        if len(info) != 2 or info[0] != "completed" or int(info[1]) > args.workspace_gib:
            parser.error("Choose a completed snapshot that fits the workspace volume")
    params = {"AvailabilityZone": az, "ImageId": ami, "InstanceType": args.instance_type,
              "RootVolumeSizeGiB": str(args.root_gib), "WorkspaceVolumeSizeGiB": str(args.workspace_gib),
              "WorkspaceSnapshotId": args.snapshot or "", **overrides}
    values = [{"ParameterKey": key, "ParameterValue": value} for key, value in params.items()]
    body = json.dumps(base, separators=(",", ":"))
    if len(body.encode()) > 51200:
        parser.error("Template exceeds CloudFormation's inline limit")
    with tempfile.TemporaryDirectory() as temp:
        path = Path(temp) / "template.json"
        path.write_text(body)
        source = "file://" + str(path)
        aws("cloudformation", "validate-template", "--template-body", source, "--query", "Description")
        print(json.dumps({"stack": args.stack, "profile": args.profile, "region": args.region,
                          "agent": args.agent, "parameters": params}, indent=2), flush=True)
        if args.plan:
            return
        stack_id = aws("cloudformation", "create-stack", "--stack-name", args.stack, "--template-body", source,
                       "--capabilities", "CAPABILITY_IAM", "--parameters", json.dumps(values),
                       "--tags", "Key=Application,Value=orca-workstation", "--query", "StackId")
    print(f"Waiting for {stack_id}", flush=True)
    wait = subprocess.run([*cli, "cloudformation", "wait", "stack-create-complete", "--stack-name", stack_id])
    if wait.returncode:
        raise SystemExit("Stack creation did not complete. Check CloudFormation events and docs/operations.md.")
    print(aws("cloudformation", "describe-stacks", "--stack-name", stack_id, "--query",
              "Stacks[0].Outputs[].[OutputKey,OutputValue]"))


if __name__ == "__main__":
    main()
