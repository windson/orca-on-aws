import json
import os
from pathlib import Path
import tempfile
import unittest
from unittest import mock

from test_reference import codex


class CatalogPackageTests(unittest.TestCase):
    def test_extracts_complete_metadata_from_nested_or_sibling_linux_packages(self):
        rows = [{"slug": name, "display_name": name} for name in codex.MODELS]
        body = b"\x7fELF\x00" + b'{"models":[null]}\x00' + json.dumps({"models": rows}).encode() + b"\xff"
        for layout in ("node_modules/@openai/codex-linux-x64", "../codex-linux-x64"):
            with self.subTest(layout=layout), tempfile.TemporaryDirectory() as tmp:
                package = Path(tmp) / "@openai/codex"
                entry = package / "bin/codex.js"
                entry.parent.mkdir(parents=True)
                entry.write_text("#!/usr/bin/env node")
                binary = package / layout / "vendor/x86_64-unknown-linux-musl/bin/codex"
                binary.parent.mkdir(parents=True)
                binary.write_bytes(body)
                with mock.patch.object(codex.shutil, "which", return_value=os.fspath(entry)), \
                     mock.patch.object(codex.subprocess, "check_output", return_value="codex-cli 0.168.0\n"):
                    self.assertEqual(list(codex.bundled_models()), list(codex.MODELS))
