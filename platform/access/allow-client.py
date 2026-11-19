#!/usr/bin/python3
"""Apply the persistent Orca device list, or add/remove a Tailscale IPv4 address."""
import argparse
import fcntl
import ipaddress
import os
from pathlib import Path
import subprocess
import tempfile

STORE = Path("/workspace/orca-access")
NET = ipaddress.ip_network("100.64.0.0/10")


def tailnet_address(value):
    address = ipaddress.ip_address(value)
    if address not in NET:
        raise ValueError("Use the client's Tailscale IPv4 address")
    return address


def rules(peers, replace):
    lines = ["delete table inet orca_access"] if replace else []
    lines.extend(["table inet orca_access {", " chain inbound {",
                  "  type filter hook input priority -20; policy accept;",
                  '  iifname "lo" tcp dport 6768 accept'])
    for peer in sorted(peers):
        lines.append(f'  iifname "tailscale0" ip saddr {peer} tcp dport 6768 accept')
    lines.extend(['  tcp dport 6768 drop', '  iifname "tailscale0" drop', ' }', '}'])
    return "\n".join(lines) + "\n"


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("action", choices=["apply", "add", "remove"])
    parser.add_argument("ip", nargs="?", type=tailnet_address)
    args = parser.parse_args()
    if (args.action == "apply") != (args.ip is None):
        parser.error("add and remove take one IPv4 address, apply takes none")
    path = STORE / "clients"
    with (STORE / "lock").open("a") as lock:
        fcntl.flock(lock, fcntl.LOCK_EX)
        peers = {tailnet_address(line) for line in path.read_text().splitlines()} if path.exists() else set()
        if args.action == "add":
            peers.add(args.ip)
        elif args.action == "remove":
            peers.discard(args.ip)
        exists = subprocess.run(["nft", "list", "table", "inet", "orca_access"],
                                stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL).returncode == 0
        batch = rules(peers, exists)
        subprocess.run(["nft", "--check", "-f", "-"], input=batch, text=True, check=True)
        with tempfile.NamedTemporaryFile(mode="w", dir=STORE, delete=False) as out:
            out.writelines(f"{ip}\n" for ip in sorted(peers))
        try:
            subprocess.run(["nft", "-f", "-"], input=batch, text=True, check=True)
            os.replace(out.name, path)
        finally:
            Path(out.name).unlink(missing_ok=True)


if __name__ == "__main__":
    main()
