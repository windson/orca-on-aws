"""Build Bedrock model metadata from the pinned, installed Codex Linux release."""
import copy
import json
import mmap
import os
from pathlib import Path
import re
import shutil
import subprocess
import sys
import tempfile

MODELS = ("gpt-6.1-sol", "gpt-6-astra", "gpt-6.1-terra", "gpt-6-sol", "gpt-6-luna",
          "gpt-5.6-sol", "gpt-5.6-terra", "gpt-5.6-luna", "gpt-5.5")
ADDITIONS = (("gpt-6.2-sol", "gpt-6.1-sol", "GPT-6.2 Sol"),
             ("gpt-6.2-astra", "gpt-6-astra", "GPT-6.2 Astra"))
FAST = [{"id": "ultrafast", "name": "Ultrafast", "description": "Separately priced speed tier."}]


def bundled_models():
    if subprocess.check_output(["codex", "--version"], text=True).strip() != "codex-cli 0.168.0":
        raise RuntimeError("Review the catalog adapter before changing the Codex release")
    entry = Path(shutil.which("codex")).resolve()
    package = entry.parent.parent
    candidates = [entry, *package.glob("**/vendor/*/bin/codex"),
                  *(package.parent / "codex-linux-x64").glob("vendor/*/bin/codex")]
    for path in candidates:
        with path.open("rb") as file:
            if file.read(4) != b"\x7fELF":
                continue
            with mmap.mmap(file.fileno(), 0, access=mmap.ACCESS_READ) as data:
                for match in re.finditer(rb'\{\s*"models"\s*:\s*\[', data):
                    window = data[match.start():match.start() + 5_000_000]
                    try:
                        blob, _ = json.JSONDecoder().raw_decode(window.decode(errors="replace"))
                        rows = {row["slug"]: row for row in blob["models"]}
                    except (KeyError, TypeError, ValueError):
                        continue
                    if all(model in rows for model in MODELS):
                        return rows
    raise RuntimeError("Bundled model metadata for the pinned release could not be located")


def catalog(bundled):
    models = {}
    for priority, slug in enumerate(MODELS):
        row = copy.deepcopy(bundled[slug])
        row.update(slug="openai." + slug, priority=priority, default_service_tier=None,
                   additional_speed_tiers=[], service_tiers=FAST if slug in MODELS[:2] else [])
        models[slug] = row
    for slug, parent, label in ADDITIONS:
        row = copy.deepcopy(models[parent])
        row.update(slug="openai." + slug, display_name=label, upgrade=None, availability_nux=None,
                   max_context_window=1050000, visibility="list", supported_in_api=True,
                   description=label + " on Amazon Bedrock.", priority=len(models),
                   default_service_tier="default" if slug.endswith("sol") else None,
                   service_tiers=[] if slug.endswith("sol") else FAST)
        models[slug] = row
    return {"models": list(models.values())}


def create_once(path, body):
    # Publishing a complete file with a hard link also preserves a concurrent writer's file.
    with tempfile.NamedTemporaryFile(mode="w", dir=path.parent, delete=False) as out:
        out.write(body)
    try:
        try:
            os.link(out.name, path)
        except FileExistsError:
            pass
    finally:
        os.unlink(out.name)


def configure(directory, region):
    if not re.fullmatch(r"[a-z]{2}(?:-[a-z0-9]+)+-\d+", region):
        raise ValueError("Invalid Bedrock region")
    directory.mkdir(exist_ok=True, parents=True, mode=0o700)
    target = directory / "models-bedrock.json"
    if not target.exists():
        create_once(target, json.dumps(catalog(bundled_models()), indent=2) + "\n")
    config = ('model = "openai.gpt-6.2-sol"\nmodel_provider = "amazon-bedrock"\n'
              'model_reasoning_effort = "xhigh"\nservice_tier = "default"\n'
              'approval_policy = "on-request"\nsandbox_mode = "workspace-write"\n'
              f'model_catalog_json = {json.dumps(str(target))}\n\n'
              f'[model_providers.amazon-bedrock.aws]\nregion = {json.dumps(region)}\n')
    create_once(directory / "config.toml", config)


if __name__ == "__main__":
    configure(Path.home() / ".codex", sys.argv[1])
