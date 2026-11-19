#!/bin/bash
set -euo pipefail
sudo -iu orca codex --version
sudo -iu orca test -s /workspace/home/.codex/config.toml
sudo -iu orca test -s /workspace/home/.codex/models-bedrock.json
if [[ "${1:-}" == --inference ]]; then
    sudo -iu orca bash -c '
        set -eu
        cd /workspace/projects
        result=$(mktemp)
        trap '\''rm -f "$result"'\'' EXIT
        codex exec --ephemeral --skip-git-repo-check --sandbox read-only \
            -o "$result" "Reply exactly ORCA_READY. Do not use tools."
        grep -Fxq ORCA_READY "$result"
    '
fi
