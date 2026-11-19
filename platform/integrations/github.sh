#!/bin/bash
# Optional operator-installed CLI. Authenticate interactively as the workstation user.
set -euo pipefail
key=$(mktemp)
trap 'rm -f "$key"' EXIT
curl --fail --silent --show-error --location --retry 3 \
    https://cli.github.com/packages/githubcli-archive-keyring.asc -o "$key"
printf '%s  %s\n' cec6e9ed82d3949ca5f4428cc968b41ef5e7416cb3653cdfc2a421977663bbfd "$key" | sha256sum -c -
install -m 0644 "$key" /etc/pki/rpm-gpg/orca-github-cli.asc
rpm --import /etc/pki/rpm-gpg/orca-github-cli.asc
cat > /etc/yum.repos.d/orca-github-cli.repo <<'REPO'
[orca-github-cli]
name=GitHub CLI
baseurl=https://cli.github.com/packages/rpm
enabled=0
gpgcheck=1
gpgkey=file:///etc/pki/rpm-gpg/orca-github-cli.asc
includepkgs=gh
REPO
dnf -y --enablerepo=orca-github-cli install gh
gh --version
