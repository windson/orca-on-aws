#!/bin/bash
set -euo pipefail
version=3.5.0
base=https://prod.download.cli.kiro.dev
fingerprint=9600944AF4B40FA81C3F6EE8724E8BC8D4F7DD61
arch=$(uname -m)
case "$arch" in
    x86_64) checksum=1c8bb34861c2f3f16c2b5906d378b38f957490266636d4c9c0fbd80f9a8fac66 ;;
    aarch64) checksum=cc513b9b0c0185c9ebec9ba7b47561b3377a493a36f6981e70e2878501a99262 ;;
    *) echo "Unsupported RPM architecture: $arch" >&2; exit 1 ;;
esac
if rpm -q kiro-cli >/dev/null 2>&1; then
    installed=$(rpm -q --qf '%{VERSION}' kiro-cli)
    if [[ "$installed" != "$version" ]]; then
        echo "Kiro CLI $installed is already installed. Review before changing to $version." >&2
        exit 1
    fi
    rpm -V kiro-cli
    /usr/bin/kiro-cli --version
    exit 0
fi

tmp=$(mktemp -d)
trap 'rm -rf -- "$tmp"' EXIT
curl --fail --silent --show-error --location --retry 2 "$base/rpm/kiro-cli.gpg" -o "$tmp/key"
mkdir -m 700 "$tmp/gnupg"
actual=$(gpg --batch --homedir "$tmp/gnupg" --with-colons --show-keys "$tmp/key" |
    awk -F: '$1 == "pub" {primary=1; next} primary && $1 == "fpr" {print $10; primary=0}')
[[ "$actual" == "$fingerprint" ]] || { echo 'Unexpected Kiro RPM signing key' >&2; exit 1; }
curl --fail --silent --show-error --location --retry 2 \
    "$base/stable/$version/kirocli-$arch-linux.rpm" -o "$tmp/kiro.rpm"
printf '%s  %s\n' "$checksum" "$tmp/kiro.rpm" | sha256sum --check --status
rpm --import "$tmp/key"
rpmkeys --checksig "$tmp/kiro.rpm"
rpm -U "$tmp/kiro.rpm"
/usr/bin/kiro-cli --version
