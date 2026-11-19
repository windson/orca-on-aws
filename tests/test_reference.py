import importlib.util
import json
from pathlib import Path
import re
import subprocess
import sys
import tempfile
import unittest
from unittest import mock

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))
import deploy
import render


def load_module(name, path):
    spec = importlib.util.spec_from_file_location(name, ROOT / path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


codex = load_module("codex_settings", "agents/codex-bedrock/configure.py")
access = load_module("orca_access", "platform/access/allow-client.py")


class PlatformTests(unittest.TestCase):
    def setUp(self):
        self.template = render.template("codex-bedrock")
        self.resources = self.template["Resources"]

    def test_render_is_self_contained_and_deterministic(self):
        self.assertEqual(self.template, render.template("codex-bedrock"))
        self.assertLess(len(json.dumps(self.template).encode()), 51200)
        host = self.resources["Host"]
        self.assertLess(len(host["Properties"]["UserData"]["Fn::Base64"]["Fn::Sub"].encode()), 16384)
        files = host["Metadata"]["AWS::CloudFormation::Init"]["config"]["files"]
        for name in ("host/mount.sh", "access/install.sh", "orca/install.sh",
                     "verify", "agent/install.sh", "agent/activate.sh", "agent/verify.sh"):
            self.assertTrue(files[render.PREFIX + "/" + name]["content"].startswith("#!"))
        self.assertEqual(files[render.PREFIX + "/agent/arguments"]["content"],
                         {"Fn::Join": ["\n", [{"Ref": "BedrockRegion"}]]})
        self.assertEqual(self.resources["Ready"]["DependsOn"], "WorkspaceAttachment")
        self.assertIn("ReadyHandle", host["Properties"]["UserData"]["Fn::Base64"]["Fn::Sub"])

    def test_planned_modules_cannot_deploy(self):
        self.assertEqual(render.supported_agents(), ["codex-bedrock", "opencode-bedrock"])
        for name in ["kiro-cli", "claude-code-bedrock", "../platform"]:
            with self.assertRaises(ValueError):
                render.template(name)
        shared = (ROOT / "infra/aws/base.json").read_text()
        self.assertNotIn("BedrockRegion", shared)
        self.assertNotIn("openai.", shared)
        self.assertNotIn("bedrock-mantle:", shared)

    def test_storage_iam_and_network_boundaries(self):
        host = self.resources["Host"]["Properties"]
        self.assertEqual(host["MetadataOptions"]["HttpTokens"], "required")
        self.assertTrue(host["BlockDeviceMappings"][0]["Ebs"]["Encrypted"])
        disk = self.resources["WorkspaceVolume"]
        self.assertEqual((disk["DeletionPolicy"], disk["UpdateReplacePolicy"]), ("Retain", "Retain"))
        self.assertTrue(disk["Properties"]["Encrypted"])
        self.assertEqual(disk["Properties"]["AvailabilityZone"], self.resources["Subnet"]["Properties"]["AvailabilityZone"])
        group = self.resources["HostSecurityGroup"]["Properties"]
        self.assertFalse(group.get("SecurityGroupIngress"))
        self.assertEqual([(r["FromPort"], r["ToPort"]) for r in group["SecurityGroupEgress"]], [(443, 443)])
        self.assertEqual(self.resources["BackupSelection"]["Properties"]["BackupSelection"]["Resources"],
                         [{"Fn::Sub": "arn:${AWS::Partition}:ec2:${AWS::Region}:${AWS::AccountId}:volume/${WorkspaceVolume}"}])
        inference = self.resources["AgentPolicy0"]["Properties"]["PolicyDocument"]["Statement"][0]
        self.assertEqual(inference["Condition"]["StringLike"]["bedrock-mantle:Model"], "openai.*")

    def test_model_catalog_and_preserved_operator_settings(self):
        bundled = {s: {"slug": s, "display_name": s} for s in codex.MODELS}
        with tempfile.TemporaryDirectory() as temp, mock.patch.object(codex, "bundled_models", return_value=bundled):
            directory = Path(temp) / ".codex"
            codex.configure(directory, "us-east-1")
            catalog = json.loads((directory / "models-bedrock.json").read_text())
            models = {x["slug"]: x for x in catalog["models"]}
            self.assertEqual(len(models), 11)
            self.assertEqual(models["openai.gpt-6.2-sol"]["default_service_tier"], "default")
            self.assertIn("openai.gpt-6.2-astra", models)
            config = directory / "config.toml"
            self.assertIn('model = "openai.gpt-6.2-sol"', config.read_text())
            self.assertIn('region = "us-east-1"', config.read_text())
            config.write_text("# operator customizations\n")
            path = directory / "models-bedrock.json"
            path.write_text("custom catalog")
            codex.configure(directory, "us-west-2")
            self.assertEqual(config.read_text(), "# operator customizations\n")
            self.assertEqual(path.read_text(), "custom catalog")

    def test_firewall_enrolls_only_explicit_clients(self):
        peer = access.tailnet_address("100.64.0.2")
        rules = access.rules({peer}, True)
        self.assertTrue(rules.startswith("delete table inet orca_access"))
        self.assertIn('iifname "lo" tcp dport 6768 accept', rules)
        self.assertIn('ip saddr 100.64.0.2 tcp dport 6768 accept', rules)
        self.assertIn('tcp dport 6768 drop', rules)
        self.assertNotIn('ip saddr', access.rules(set(), False))
        for outside in ("192.0.2.2", "::1", "100.64.0.0/10"):
            with self.assertRaises(ValueError):
                access.tailnet_address(outside)

    def test_document_links_resolve_and_have_no_local_absolute_paths(self):
        for file in ROOT.rglob("*.md"):
            for link in re.findall(r"\[[^\]]+\]\(([^)]+)\)", file.read_text()):
                if link.startswith(("https://", "#")):
                    continue
                self.assertFalse(Path(link).is_absolute(), (file, link))
                self.assertTrue((file.parent / link.split("#")[0]).exists(), (file, link))


class DeployTests(unittest.TestCase):
    def simulate(self, extra):
        commands = []
        def check(command, **options):
            commands.append(command)
            if "describe-instance-type-offerings" in command:
                return "us-east-1b\tus-east-1a"
            if "get-parameter" in command:
                return "example-ami"
            if "validate-template" in command or "create-stack" in command:
                body = next(v[7:] for v in command if v.startswith("file://"))
                self.assertIn("Ready", json.loads(Path(body).read_text())["Resources"])
            if "create-stack" in command:
                return "example-stack-id"
            return ""
        with mock.patch.object(sys, "argv", ["deploy", "--stack", "example", *extra]), \
             mock.patch.object(subprocess, "check_output", side_effect=check), \
             mock.patch.object(subprocess, "run") as run, mock.patch("builtins.print"):
            run.return_value.returncode = 0
            deploy.main()
        return commands, run

    def test_plan_issues_read_only_calls(self):
        commands, run = self.simulate(["--plan"])
        self.assertEqual(len(commands), 3)
        self.assertTrue(all("default" in cmd for cmd in commands))
        self.assertFalse(any("create-stack" in cmd for cmd in commands))
        run.assert_not_called()

    def test_create_passes_selected_region_and_waits_for_bootstrap(self):
        commands, run = self.simulate(["--profile", "demo", "--parameter", "BedrockRegion=us-west-2"])
        create = next(cmd for cmd in commands if "create-stack" in cmd)
        params = {p["ParameterKey"]: p["ParameterValue"] for p in json.loads(create[create.index("--parameters") + 1])}
        self.assertEqual(params["BedrockRegion"], "us-west-2")
        self.assertEqual(params["AvailabilityZone"], "us-east-1a")
        self.assertIn("demo", create)
        self.assertIn("stack-create-complete", run.call_args.args[0])
