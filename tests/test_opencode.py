import importlib.util
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))
import add_opencode
import render

spec = importlib.util.spec_from_file_location("opencode_configure", add_opencode.MODULE / "configure.py")
config = importlib.util.module_from_spec(spec)
spec.loader.exec_module(config)


class OpenCodeTests(unittest.TestCase):
    def test_system_policy_enables_only_bedrock_without_filtering_models(self):
        policy = json.loads((add_opencode.MODULE / "managed.json").read_text())
        self.assertEqual(policy, {"enabled_providers": ["amazon-bedrock"]})
        host = render.template("opencode-bedrock")["Resources"]["Host"]
        files = host["Metadata"]["AWS::CloudFormation::Init"]["config"]["files"]
        self.assertEqual(json.loads(files[render.PREFIX + "/agent/managed.json"]["content"]), policy)

    def test_default_preserves_catalog_and_owner_settings(self):
        with tempfile.TemporaryDirectory() as d:
            root = Path(d)
            config.configure(root, "us-east-1", root)
            path = root / ".config/opencode/opencode.json"
            data = json.loads(path.read_text())
            self.assertEqual(set(data), {"$schema", "model", "provider"})
            self.assertEqual(set(data["provider"]["amazon-bedrock"]), {"options"})
            data["model"] = "operator/choice"
            path.write_text(json.dumps(data))
            config.configure(root, "us-east-1", root)
            self.assertEqual(json.loads(path.read_text()), data)
            with self.assertRaises(ValueError):
                config.configure(root, "us-west-2", root)

    def test_addon_and_fresh_host_use_the_same_module(self):
        manifest = json.loads((add_opencode.MODULE / "agent.json").read_text())
        fresh = render.template("opencode-bedrock")
        self.assertEqual(fresh["Resources"]["AgentPolicy0"]["Properties"]["PolicyDocument"],
                         manifest["policies"][0]["PolicyDocument"])
        policy = add_opencode.policy_document(manifest, "arn:aws:iam::example:role/test", "us-east-1")
        self.assertNotIn("Fn::Sub", json.dumps(policy))
        self.assertIn("bedrock:InferenceProfileArn", json.dumps(policy))
        self.assertNotIn("iam:", json.dumps(policy))
        self.assertNotIn("aws-marketplace:", json.dumps(policy))
        cmd = add_opencode.host_command(manifest, "us-east-1")
        subprocess.run(["bash", "-n"], input=cmd, text=True, check=True)
        self.assertNotIn("systemctl restart", cmd)
        self.assertLess(len(json.dumps(fresh).encode()), 51200)
