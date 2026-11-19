#!/usr/bin/python3
"""Prepare Orca's default worktree root before starting the headless server."""
import json
import os
from pathlib import Path
import shutil
import sqlite3
import subprocess
import sys
import tempfile


LEGACY = "/home/ec2-user/orca/workspaces"
SERVER = Path("/opt/orca-server")


def saved_settings(database, data_file):
    if database is not None and database.is_file():
        with sqlite3.connect(database.as_uri() + "?mode=ro", uri=True) as db:
            row = db.execute("SELECT payload FROM profile_state_documents WHERE domain='settings'").fetchone()
        return json.loads(row[0]) if row else {}
    return json.loads(data_file.read_text())["settings"] if data_file.exists() else {}


def recover_json(profile, state):
    # The pinned Linux wrapper sets ELECTRON_RUN_AS_NODE. The recovery command
    # would then try to start Electron on a server-only host. Use its Node CLI.
    node, = (SERVER / "runtimes").glob("node-*/bin/node")
    env = dict(os.environ, ORCA_USER_DATA_PATH=str(state))
    for key in ("ELECTRON_RUN_AS_NODE", "ORCA_APP_EXECUTABLE"):
        env.pop(key, None)
    completed = subprocess.run(
        [str(node), str(SERVER / "orcad/out/cli/index.js"), "profile", "state", "rollback",
         "--latest-json", "--profile-id", profile, "--json"],
        env=env, capture_output=True, text=True, check=True,
    )
    reply = json.loads(completed.stdout)
    if not reply["ok"] or reply["result"]["storage"] != "json":
        raise RuntimeError("Orca could not export the current profile")
    return Path(reply["result"]["restoredPath"])


def prepare(state, target):
    index = state / "orca-profile-index.json"
    data_file = state / "orca-data.json"
    database = None
    if index.exists() or index.with_suffix(".json.bak").exists():
        # Orca resolves the active profile, including its backup index.
        result = subprocess.run(
            [str(SERVER / "bin/orca-ide"), "profile", "state", "exports", "--json"],
            env=dict(os.environ, ORCA_USER_DATA_PATH=str(state)),
            capture_output=True, text=True, check=True,
        )
        profile = json.loads(result.stdout)["result"]
        data_file, database = Path(profile["dataFile"]), Path(profile["databaseFile"])
    settings = saved_settings(database, data_file)
    current = settings.get("workspaceDir")
    if current not in (None, LEGACY, str(target)):
        return  # Keep operator-selected roots and all repository-specific overrides.
    if current == LEGACY and os.access(LEGACY, os.W_OK | os.X_OK):
        return
    target.mkdir(mode=0o700, parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(dir=target, prefix=".orca-write-check-"):
        pass
    if current != LEGACY:
        return

    # Orca archives its SQLite database and exports the latest revision. On the
    # next startup it imports the edited JSON through its own migration code.
    if database and database.exists():
        if recover_json(profile["profileId"], state) != data_file:
            raise RuntimeError("Unexpected Orca recovery path")
    document = json.loads(data_file.read_text())
    settings = document["settings"]
    if settings["workspaceDir"] != LEGACY:
        raise RuntimeError("Workspace setting changed during migration")
    with tempfile.NamedTemporaryFile(dir=data_file.parent, prefix="before-worktree-root-", delete=False) as backup:
        with data_file.open("rb") as original:
            shutil.copyfileobj(original, backup)
        backup.flush()
        os.fsync(backup.fileno())
    previous = {"path": LEGACY, "nestWorkspaces": settings.get("nestWorkspaces", True)}
    history = settings.setdefault("workspaceDirHistory", [])
    if previous not in history:
        history.append(previous)
    settings["workspaceDir"] = str(target)
    with tempfile.NamedTemporaryFile(dir=data_file.parent, mode="w", delete=False) as tmp:
        pending = Path(tmp.name)
        try:
            json.dump(document, tmp, ensure_ascii=False, separators=(",", ":"))
            tmp.flush()
            os.fsync(tmp.fileno())
            os.replace(pending, data_file)
        finally:
            pending.unlink(missing_ok=True)
    print("Repaired the inherited Orca worktree directory.")


if __name__ == "__main__":
    if os.geteuid() == 0:
        sys.exit("Run as the Orca service user while the server is stopped.")
    target = Path(sys.argv[1]).resolve()
    if Path("/workspace") not in target.parents or not os.path.ismount("/workspace"):
        sys.exit("Expected a worktree root on the mounted /workspace volume.")
    prepare(Path(os.environ["ORCA_USER_DATA_PATH"]), target)
