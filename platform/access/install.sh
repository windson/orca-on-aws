#!/bin/bash
set -euo pipefail
dnf -y install nftables
curl --fail --silent --show-error --location --retry 3 \
    https://pkgs.tailscale.com/stable/amazon-linux/2023/tailscale.repo -o /etc/yum.repos.d/tailscale.repo
dnf -y install tailscale
[[ ! -L /workspace/tailscale && ! -L /workspace/orca-access ]]
install -d -m 0700 /workspace/tailscale /workspace/orca-access
install -D -m 0644 /opt/orca-workstation/access/firewall.service /etc/systemd/system/orca-access.service
install -d /etc/systemd/system/tailscaled.service.d
cat > /etc/systemd/system/tailscaled.service.d/workspace.conf <<'UNIT'
[Unit]
RequiresMountsFor=/workspace
[Service]
ExecStart=
ExecStart=/usr/sbin/tailscaled --state=/workspace/tailscale/tailscaled.state --socket=/run/tailscale/tailscaled.sock --port=41641
UNIT
systemctl daemon-reload
systemctl enable --now orca-access tailscaled
systemctl disable --now sshd.service
