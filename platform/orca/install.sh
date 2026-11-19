#!/bin/bash
set -euo pipefail
version=1.4.258
digest=fd7f23f5fb6fe43fb2982d17438d772fac7cc65c8208a212d0ffb224b504e311
dir=$(mktemp -d)
trap 'rm -rf "$dir"' EXIT
curl --fail --silent --show-error --location --retry 3 \
    "https://github.com/stablyai/orca/releases/download/v$version/orca-server-linux-x64.tar.gz" -o "$dir/orca.tgz"
printf '%s  %s\n' "$digest" "$dir/orca.tgz" | sha256sum --check -
install -d /opt/orca-server
tar -xzf "$dir/orca.tgz" --no-same-owner --strip-components=1 -C /opt/orca-server
install -m 0755 /opt/orca-workstation/orca/session /usr/local/bin/orca-host
install -m 0644 /opt/orca-workstation/orca/server.service /etc/systemd/system/orca-server.service
loginctl enable-linger orca
systemctl start user@2200.service
systemctl daemon-reload
systemctl enable --now orca-server
