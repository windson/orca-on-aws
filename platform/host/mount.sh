#!/bin/bash
set -euo pipefail
volume=$1
snapshot=$2
serial=$(tr -d '-' <<< "$volume")
device=''
for ((i=0; i<120; i++)); do
    device=$(lsblk -dnpo PATH,SERIAL | awk -v serial="$serial" '$2==serial {print $1}')
    if [[ -b "$device" ]]; then break; fi
    sleep 2
done
[[ -b "$device" && "$(lsblk -nrpo NAME "$device" | wc -l)" -eq 1 ]]
fstype=$(lsblk -dno FSTYPE "$device")
if [[ -z "$fstype" ]]; then
    [[ -z "$snapshot" && -z "$(wipefs --noheadings -o TYPE "$device")" ]]
    mkfs.xfs "$device"
elif [[ "$fstype" != xfs ]]; then
    echo 'Expected an XFS workspace disk.' >&2
    exit 1
fi
uuid=$(blkid -s UUID -o value "$device")
install -d /workspace
if findmnt -M /workspace >/dev/null; then
    [[ "$(findmnt -n -M /workspace -o UUID)" == "$uuid" ]]
else
    if awk '$2=="/workspace" {found=1} END {exit !found}' /etc/fstab; then
        awk -v id="UUID=$uuid" '$1==id && $2=="/workspace" {ok=1} END {exit !ok}' /etc/fstab
    else
        printf 'UUID=%s /workspace xfs defaults,nofail 0 2\n' "$uuid" >> /etc/fstab
    fi
    mount /workspace
fi
if [[ -n "$snapshot" ]]; then
    [[ ! -L /workspace/.orca-workstation-layout ]]
    grep -Fxq 'orca-workstation-v1' /workspace/.orca-workstation-layout
else
    printf '%s\n' 'orca-workstation-v1' > /workspace/.orca-workstation-layout
fi
xfs_growfs /workspace
# Retained home ownership must match after a restore. Never reassign another UID.
if ! id orca >/dev/null 2>&1; then
    useradd --no-create-home --user-group --uid 2200 --home-dir /workspace/home --shell /bin/bash orca
fi
[[ "$(id -u orca)" == 2200 && "$(getent passwd orca | cut -d: -f6)" == /workspace/home ]]
for path in /workspace/home /workspace/projects /workspace/orca-state; do
    [[ ! -L "$path" ]]
    if [[ -e "$path" ]]; then [[ -d "$path" && "$(stat -c %u "$path")" == 2200 ]]; fi
    install -d -o orca -g orca -m 0700 "$path"
done
systemctl daemon-reload
