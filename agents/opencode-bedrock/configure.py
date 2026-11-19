"""Configure the service user's Bedrock provider without hard-coding a model menu."""
import json
import os
from pathlib import Path
import re
import subprocess
import sys
import tempfile

DEFAULT = "amazon-bedrock/openai.gpt-oss-20b-1:0"


def new_json(path, value):
    with tempfile.NamedTemporaryFile(mode="w", dir=path.parent, delete=False) as stream:
        json.dump(value, stream, indent=2)
        stream.write("\n")
    try:
        os.link(stream.name, path)
    finally:
        os.unlink(stream.name)


def check_provider(item, region):
    settings = item.get("provider", {}).get("amazon-bedrock", {})
    if settings.get("options", {}).get("region") != region:
        raise ValueError(f"Set the existing amazon-bedrock provider's region to {region} before retrying")


def configure(home, region, workspace=Path("/workspace"), binary="opencode"):
    if not re.fullmatch(r"[a-z]{2}(?:-[a-z0-9]+)+-\d+", region):
        raise ValueError("Invalid Bedrock region")
    cfg = home / ".config/opencode"
    cfg.mkdir(parents=True, exist_ok=True, mode=0o700)
    config = cfg / "opencode.json"
    # Reference hosts retain the whole home. Earlier workstations retain this writable directory.
    retained = None
    if home.stat().st_dev != workspace.stat().st_dev:
        retained = workspace / "orca-credentials/opencode"
        retained.mkdir(mode=0o700, exist_ok=True)
        for sub in (".local/share", ".local/state"):
            dest = retained / Path(sub).name
            local = home / sub / "opencode"
            if (local.exists() or local.is_symlink()) and local.resolve() != dest.resolve():
                raise ValueError("Migrate existing OpenCode data to retained storage before installation")
            dest.mkdir(mode=0o700, exist_ok=True)
            local.parent.mkdir(exist_ok=True, parents=True)
            if not local.is_symlink():
                local.symlink_to(dest, target_is_directory=True)
    if (cfg / "opencode.jsonc").exists():
        # Use OpenCode's JSONC parser. The effective configuration stays on the host.
        result = subprocess.run([binary, "debug", "config"], cwd=home, capture_output=True, check=True,
                                text=True, timeout=60)
        check_provider(json.loads(result.stdout), region)
        return
    if config.exists():
        check_provider(json.loads(config.read_text()), region)
        return
    target = retained / "opencode.json" if retained else config
    if target.exists():
        check_provider(json.loads(target.read_text()), region)
    else:
        new_json(target, {"$schema": "https://opencode.ai/config.json", "model": DEFAULT,
                          "provider": {"amazon-bedrock": {"options": {"region": region, "profile": "default"}}}})
    if retained:
        config.symlink_to(target)


if __name__ == "__main__":
    configure(Path.home(), sys.argv[1], binary=sys.argv[2])
