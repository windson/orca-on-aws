# Orca workstation on AWS

Deploy a persistent Linux workstation for Orca Desktop and Android. Codex and OpenCode can share one workstation and use Amazon Bedrock inference. Projects, agent configuration, and Orca pairing state live on a separate encrypted disk. A paired phone connects directly to EC2 through Tailscale, including when the laptop is asleep.

| Agent | Status | Inference |
| --- | --- | --- |
| [Codex](agents/codex-bedrock/README.md) | Deployable | Amazon Bedrock, GPT-6.2 Sol by default |
| [OpenCode](agents/opencode-bedrock/README.md) | Fresh host or add to existing Orca | Bedrock only, full upstream Bedrock picker |
| [Kiro CLI](agents/kiro-cli/README.md) | Planned | To be specified |
| [Claude Code](agents/claude-code-bedrock/README.md) | Planned | Amazon Bedrock |

## Deploy

Use Python 3.9+, AWS CLI v2, an AWS CLI profile with deployment permissions, and a region with the chosen instance type. Install the AWS Session Manager plugin on your computer for the first connection. Install Orca Desktop or Orca Mobile on the clients you want to pair. Mobile also needs a Tailscale account and the Tailscale app. [AWS CLI installation](https://docs.aws.amazon.com/cli/latest/userguide/getting-started-install.html) · [Session Manager plugin](https://docs.aws.amazon.com/systems-manager/latest/userguide/session-manager-working-with-install-plugin.html) · [Orca releases](https://github.com/stablyai/orca/releases) · [Tailscale clients](https://tailscale.com/download)

1. From a clone of this repository, check your AWS identity and preview the deployment. The preview resolves the AMI and an offered availability zone, then submits the generated template to CloudFormation for validation.

   ```sh
   aws sts get-caller-identity --profile default
   python3 tools/deploy.py --stack orca-dev --region us-east-1 --plan
   ```

2. Create the workstation with a new stack name. Creation waits for the disk mount, Orca listener, owner CLI, and agent setup. The command prints the instance ID, backup vault, and workspace volume ID. Reusing an existing stack name returns an error.

   ```sh
   python3 tools/deploy.py --stack orca-dev --region us-east-1
   ```

3. Open an administrative session from the same computer. The following commands are for a POSIX shell. On Windows, use WSL or pass the instance ID from the stack outputs to the AWS CLI in PowerShell.

   ```sh
   HOST_ID=$(aws cloudformation describe-stacks --stack-name orca-dev --region us-east-1 --profile default \
     --query "Stacks[0].Outputs[?OutputKey=='InstanceId'].OutputValue | [0]" --output text)
   aws ssm start-session --target "$HOST_ID" --region us-east-1 --profile default
   ```

4. Inside that session, run one small inference request. A successful check ends with exit code zero after Codex returns `ORCA_READY`. This request incurs Bedrock usage. Then pair each client and add your Git checkout to the remote host. [Desktop and Android pairing](docs/access.md) · [Codex setup and first chat](agents/codex-bedrock/README.md)

   ```sh
   sudo /opt/orca-workstation/agent/verify.sh --inference
   ```

The example uses a `t3.large`, a 30 GiB root disk, a 150 GiB workspace, and daily backups kept for 14 days. EC2, EBS, snapshots, public IPv4, detailed monitoring, and Bedrock usage can incur charges. A GPU is optional for project workloads. Inspect the account's Bedrock access and EC2 quotas before deployment. [Capacity, costs, backup and teardown](docs/operations.md) · [AWS Pricing Calculator](https://calculator.aws/)

## Layout

| Directory | Responsibility |
| --- | --- |
| `infra/aws/` | VPC, EC2, storage, backup and shared IAM |
| `platform/host/` | First boot, workspace mount and health checks |
| `platform/orca/` | Pinned Orca server, systemd service and optional worktree dependency setup |
| `platform/access/` | Tailscale enrollment support and host firewall |
| `platform/integrations/` | Optional tools shared by agents, currently GitHub CLI |
| `agents/<name>/` | One coding agent's packages, inference permissions, configuration and checks |
| `tools/` | Compose the template and deploy to a fresh stack |
| `tests/` | Offline regression checks |

Run `python3 -m unittest discover -s tests` to test a checkout. Use `python3 tools/render.py > template.json` to inspect the standalone template. All host setup files are embedded in the rendered output. The instance downloads published packages during boot and needs no access to a fork of this repository. [Workspace setup and GitHub](docs/workspaces.md) · [Agent module contract](agents/README.md) · [Access and IAM design](docs/security.md)

The MIT license covers the reference code. Orca, Codex, Tailscale and other distributed software retain their respective licenses. This is an independent deployment reference.
