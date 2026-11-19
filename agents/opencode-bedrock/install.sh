#!/bin/bash
set -euo pipefail
region=$1
user=${ORCA_RUN_USER:-orca}
module=$(cd -- "$(dirname -- "$0")" && pwd)
version=1.19.6
sha=47734e08968b30cc22a0bffb6d9feeed76ad4aa743213a12122040392d09a057
release=/opt/orca-opencode/$version
[[ $(uname -m) == x86_64 ]]
if ! command -v git >/dev/null; then dnf -y install git; fi
exec 9>/run/lock/orca-opencode-install.lock
flock 9
if [[ -e /usr/local/bin/opencode || -L /usr/local/bin/opencode ]]; then
    case $(readlink /usr/local/bin/opencode || true) in
        /opt/orca-opencode/*/opencode) ;;
        *) echo 'An independently managed OpenCode installation exists.' >&2; exit 1 ;;
    esac
fi
stage=$(mktemp -d)
trap 'rm -rf "$stage"' EXIT
if [[ ! -x "$release/opencode" ]]; then
    curl --fail --silent --show-error --location --retry 3 \
        "https://github.com/anomalyco/opencode/releases/download/v$version/opencode-linux-x64.tar.gz" -o "$stage/release.tgz"
    printf '%s  %s\n' "$sha" "$stage/release.tgz" | sha256sum --check -
    tar --no-same-owner -xzf "$stage/release.tgz" -C "$stage"
    install -d -m 0755 "$release"
    install -m 0755 "$stage/opencode" "$release/opencode.new"
    mv -T "$release/opencode.new" "$release/opencode"
fi
[[ $("$release/opencode" --version) == "$version" ]]
# OpenCode loads the system JSONC after user, project and inline configuration.
# Preserve an administrator's existing file and check its effective policy in verify.sh.
install -d -m 0755 /etc/opencode
managed=/etc/opencode/opencode.jsonc
if [[ ! -e "$managed" && ! -L "$managed" ]]; then
    install -m 0644 "$module/managed.json" "$managed"
fi
# Install the user configuration before exposing a new agent in Orca.
sudo -Hu "$user" -- python3 "$module/configure.py" "$region" "$release/opencode"
ln -s "$release/opencode" /usr/local/bin/.orca-opencode-link.$$
mv -Tf /usr/local/bin/.orca-opencode-link.$$ /usr/local/bin/opencode
