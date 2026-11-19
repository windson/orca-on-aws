"""Assemble a standalone CloudFormation template from the platform and one agent."""
import argparse
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PREFIX = "/opt/orca-workstation"
PLATFORM_FILES = {
    "host/mount.sh": "platform/host/mount.sh",
    "orca/install.sh": "platform/orca/install.sh",
    "orca/server.service": "platform/orca/server.service",
    "orca/prepare-worktrees.py": "platform/orca/prepare-worktrees.py",
    "github/install.sh": "platform/integrations/github.sh",
    "orca/setup-workspace.sh": "platform/orca/setup-workspace.sh",
    "orca/session": "platform/orca/session",
    "access/install.sh": "platform/access/install.sh",
    "access/allow-client": "platform/access/allow-client.py",
    "access/firewall.service": "platform/access/firewall.service",
    "verify": "platform/host/verify.sh",
}


def supported_agents():
    return sorted(p.parent.name for p in (ROOT / "agents").glob("*/agent.json"))


def template(agent):
    if agent not in supported_agents():
        raise ValueError(f"Choose an implemented agent from {supported_agents()}")
    agent_dir = ROOT / "agents" / agent
    module = json.loads((agent_dir / "agent.json").read_text())
    base = json.loads((ROOT / "infra/aws/base.json").read_text())
    base["Parameters"].update(module["parameters"])
    base["Outputs"].update(module["outputs"])
    resources = base["Resources"]
    for index, policy in enumerate(module["policies"]):
        key = f"AgentPolicy{index}"
        resources[key] = {"Type": "AWS::IAM::ManagedPolicy",
                          "Properties": {"Description": policy["PolicyName"],
                                         "PolicyDocument": policy["PolicyDocument"]}}
        resources["HostRole"]["Properties"]["ManagedPolicyArns"].append({"Ref": key})
    assets = {dst: ROOT / src for dst, src in PLATFORM_FILES.items()}
    for name in module["files"]:
        if Path(name).name != name:
            raise ValueError(f"Expected a module filename, got {name}")
        assets["agent/" + name] = agent_dir / name
    files = {f"{PREFIX}/{dst}": {"content": path.read_text(), "mode": "000755",
             "owner": "root", "group": "root"} for dst, path in assets.items()}
    files[f"{PREFIX}/agent/arguments"] = {
        "content": {"Fn::Join": ["\n", module["installArgs"]]},
        "mode": "000644", "owner": "root", "group": "root",
    }
    host = resources["Host"]
    host["Metadata"] = {"AWS::CloudFormation::Init": {"config": {"files": files}}}
    host["Properties"]["UserData"] = {"Fn::Base64": {"Fn::Sub":
        (ROOT / "platform/host/user-data.sh").read_text()}}
    resources["ReadyHandle"] = {"Type": "AWS::CloudFormation::WaitConditionHandle"}
    resources["Ready"] = {
        "Type": "AWS::CloudFormation::WaitCondition", "DependsOn": "WorkspaceAttachment",
        "Properties": {"Handle": {"Ref": "ReadyHandle"}, "Timeout": "2400", "Count": 1},
    }
    return base


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--agent", choices=supported_agents(), default="codex-bedrock")
    args = parser.parse_args()
    print(json.dumps(template(args.agent), indent=2))


if __name__ == "__main__":
    main()
