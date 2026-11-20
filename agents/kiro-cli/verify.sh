#!/bin/bash
set -euo pipefail
user=${ORCA_RUN_USER:-orca}
cli=/opt/orca-server/bin/orca-ide
sudo -Hu "$user" /usr/bin/kiro-cli --version
sudo -Hu "$user" /usr/bin/kiro-cli acp --help >/dev/null
pid=$(systemctl show orca-server -p MainPID --value)
[[ "$pid" =~ ^[1-9][0-9]*$ ]] || { echo 'Orca server is not running' >&2; exit 1; }
# SSM and Orca terminals can see different write permissions for the same file.
nsenter --target "$pid" --mount -- sudo -Hu "$user" python3 - <<'PY'
from pathlib import Path
import sqlite3
import tempfile

home = Path.home()
data = home / ".local/share/kiro-cli"
for path in (data, home / ".kiro"):
    existed = path.is_dir()
    if not existed:
        # The first login creates these directories. Probe its nearest existing parent.
        path = next(parent for parent in path.parents if parent.is_dir())
    with tempfile.TemporaryDirectory(dir=path):
        pass
db_path = data / "data.sqlite3"
if db_path.exists():
    db = sqlite3.connect(db_path.as_uri() + "?mode=rw", uri=True, timeout=5)
    try:
        db.execute("BEGIN IMMEDIATE")
        db.execute("CREATE TABLE orca_kiro_write_probe (probe INTEGER)")
        db.rollback()
    finally:
        db.close()
print("Kiro can write its state inside the Orca service")
PY
sudo -Hu "$user" env ORCA_USER_DATA_PATH=/workspace/orca-state "$cli" agent installed --json |
    python3 -c '
import json, sys
reply = json.load(sys.stdin)
if not reply.get("ok") or not any(a["id"] == "kiro" for a in reply["result"]["agents"]):
    sys.exit("Orca could not discover Kiro. Check the host agent settings and PATH.")
print("Orca detects Kiro")
'
