# Operation and recovery

## Size and region

Bedrock runs inference in its service region. Size EC2 for the work that executes in Orca, including builds, browsers, SDKs, and parallel terminals. A GPU is useful when project code uses CUDA. Check regional offerings and GPU quotas. For example, preview an A10G workstation with 8 vCPUs and 32 GiB RAM using the following command.

```sh
python3 tools/deploy.py --stack orca-gpu --region us-east-1 \
  --instance-type g5.2xlarge --root-gib 50 --workspace-gib 250 --plan
```

Choose a compatible x86_64 Amazon Linux 2023 AMI with the NVIDIA driver installed, or install and verify a supported driver as the administrator. Pass a tested AMI with `--ami-id` and select the intended zone with `--az`. The normal Amazon Linux image installs the workstation software only. Run `nvidia-smi` and a representative SDK operation in the Orca session that will use the GPU. Keep durable data on `/workspace`. Instance-store NVMe is disposable.

The pin for Orca is in `platform/orca/install.sh` and Codex's pin is in its agent directory. Record the exact AMI ID and sizes from the preview to repeat a build. Tailscale and OS RPMs come from the configured repositories at install time. The AWS Backup service must be available in the EC2 region. Use **AWS Backup → Jobs** to verify the first completed workspace recovery point and periodically test restores.

## Updates and debugging

`deploy.py` only creates new stacks. Use a new name to test changes. CloudFormation user data runs on first boot. Applying an in-place template update can replace disks or hosts and does not reinstall all host components. Schedule OS and agent updates, review volume changes and make a recovery point before maintenance.

The root disk holds OS packages and systemd units. The separate workspace holds `home/` (including agent and Orca credentials), `projects/`, `orca-state/`, the root-owned Tailscale identity and the client allowlist. AWS Backup selects only the workspace volume, daily at 05:00 UTC with 14-day retention. Changes made only to the root disk, including installed SDKs, need their own reproducible installer or AMI.

During boot inspect stack events, `/var/log/cloud-init-output.log`, `/var/log/cfn-init.log`, and `journalctl -u orca-server`. CloudFormation waits up to 40 minutes for first-boot success. An early failure to install the signaling utility can reach that timeout. A failed deployment can leave a retained disk and vault. Use the stack's resource inventory to locate them.

## Restore a workspace

Use a completed, trusted, same-region EBS snapshot of a workspace created by this reference. AWS Backup-managed recovery points can be restored as EBS volumes through AWS Backup. If using a restored volume, take an EBS snapshot of that volume and supply its snapshot ID. The requested workspace size must be at least the snapshot's size. Stop the original host before starting a restored copy with the same Tailscale and Orca identities.

```sh
python3 tools/deploy.py --stack orca-restored --region us-east-1 \
  --snapshot "$SNAPSHOT_ID" --workspace-gib 150
```

The mount script matches the EBS serial, checks the XFS filesystem and layout marker, then expands it to the requested size. The retained user has a fixed UID. Review the restored configuration's Bedrock region, projects and device list. Run the on-host checks and reconnect one paired device. Legacy layouts need an explicit, reviewed migration.

## Stop or delete

Stopping the EC2 instance takes Orca offline and stops instance compute charges. EBS and backups can continue to incur charges. For permanent teardown, first record the region, stack outputs and the recovery point you want to keep. Finish active work, stop the instance and wait for it to stop so the workspace can detach cleanly.

```sh
aws cloudformation describe-stacks --stack-name orca-dev --profile default --region us-east-1 \
  --query 'Stacks[0].Outputs' --output table
aws ec2 stop-instances --instance-ids "$HOST_ID" --profile default --region us-east-1
aws ec2 wait instance-stopped --instance-ids "$HOST_ID" --profile default --region us-east-1
aws cloudformation delete-stack --stack-name orca-dev --profile default --region us-east-1
aws cloudformation wait stack-delete-complete --stack-name orca-dev --profile default --region us-east-1
```

The workspace disk and backup vault are retained. When permanently decommissioning, confirm the disk ID against your saved output and check it is detached. Delete that volume if you no longer need its data. Remove any unwanted recovery points under the vault's retention policy, then delete the empty vault. Include any separately created snapshots or restore-test volumes in your cleanup. Remove the old machine and paired devices from the tailnet and Orca clients.
