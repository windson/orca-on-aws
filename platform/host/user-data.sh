#!/bin/bash
# shellcheck disable=SC2016
# CloudFormation substitutes the stack, region, disk and completion handle.
set -euo pipefail
umask 022
dnf -y install aws-cfn-bootstrap
signal_result() {
    result=$?
    /opt/aws/bin/cfn-signal -e "$result" '${ReadyHandle}' || exit 1
    exit "$result"
}
trap signal_result EXIT
/opt/aws/bin/cfn-init -v --stack '${AWS::StackName}' --resource Host --region '${AWS::Region}'
cd /opt/orca-workstation
dnf -y install git
snapshot='${WorkspaceSnapshotId}'
host/mount.sh '${WorkspaceVolume}' "$snapshot"
access/install.sh
xargs -d "\n" agent/install.sh < agent/arguments
orca/install.sh
./verify
if [[ -z "$snapshot" ]]; then
    agent/activate.sh
fi
