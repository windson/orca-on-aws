# Access and IAM

Use this reference for a single trusted operator or a group sharing the same workstation privileges. A paired Orca client can run code as the Linux user and read its projects. Give each independent trust boundary its own workstation and instance role.

| Boundary | Default |
| --- | --- |
| AWS network | Dedicated VPC, one subnet, one public IPv4 for outbound access, internet gateway, zero inbound security group rules, outbound TCP 443 |
| Private access | Session Manager for administration, Tailscale IPv4 with a per-client EC2 firewall rule for Orca, followed by application-level pairing |
| Linux | Dedicated `orca` user without sudo, service with no capabilities or privilege escalation, protected OS files, writable project, home and Orca state |
| AWS identity | Instance profile, IMDSv2 required, hop limit one, SSM managed-node permissions, explicit deny on Parameter Store reads, selected agent's inference policy |
| Persistence | Encrypted EBS, encrypted backups of the workspace, root-only Tailscale identity, private user home and Orca state |

The deployer's AWS profile needs CloudFormation, EC2/VPC/EBS, Backup, IAM role and policy creation and `iam:PassRole`, plus SSM AMI lookup. The human who administers the host needs permission to start an SSM session. The default SSM shell can use sudo. For a desktop that only needs the dashboard, use Tailscale plus Orca pairing or a dedicated AWS identity restricted to the specific host and an approved port-forwarding document. Do not give mobile users the deployer's profile.

Code running as the workstation user can use the instance role. Codex's Bedrock policy limits inference to OpenAI models in the selected account and region. The backup role is separate. Add project-specific AWS access deliberately and scope it to the project. The reference grants no general IAM administration or SDK installation through sudo.

## Which permission to change

| Symptom or requirement | Where authority lives | How to check it |
| --- | --- | --- |
| The agent discovers a model but Bedrock denies an inference request | The EC2 instance profile supplies temporary credentials. The selected agent's IAM policy must allow the operation, model route and region. OpenCode adds Bedrock Runtime and inference-profile access for the models it uses. | Run a small request with the intended model from a fresh agent session. |
| A project needs to deploy AWS resources | Grant use of a separately administered, project-scoped deployment role to the intended workstation. Scope that role to the project's resources and actions. Keep changes to the role's trust and permissions with its administrator. | Check the acting identity inside the deployment workflow and test its smallest required action. |
| A Python SDK cannot install into its project or open the GPU | The Orca Linux user's directory ownership, device access and service restrictions apply. Use a writable project environment. An administrator owns OS packages, GPU drivers and any service device overrides. | Check the paths and device access inside the actual agent or terminal process. Run the [CUDA calculation](operations.md#size-and-region) there. |
| A command still asks for confirmation | A fresh turn uses the agent's effective approval policy. Full access can run commands under the process's existing OS and AWS permissions. | Start a new turn after changing Orca's picker and check its effective policy. |

These choices arose on the deployed host when an additional agent needed Bedrock APIs, a project needed deployment permissions, and a local SDK needed CUDA. Fresh installations use the selected agent's inference policy and the reference's protected service account. An operator who adds project deployment access must also review that role's trust, grants and permissions boundary independently. [EC2 instance roles](https://docs.aws.amazon.com/AWSEC2/latest/UserGuide/iam-roles-for-amazon-ec2.html) · [IAM role permissions](https://docs.aws.amazon.com/IAM/latest/UserGuide/id_roles_manage_modify.html)

## Network review

The AWS IaC MCP security rules flag the public IPv4, internet gateway default route, and HTTPS egress to any IPv4 destination. These support package downloads, Bedrock, SSM and Tailscale's HTTPS relay. There is no listening port allowed by the AWS security group. The scanner also flags missing instance-level `SubnetId`. The template assigns the host to its VPC subnet in `NetworkInterfaces[0].SubnetId`; setting both properties is invalid in EC2. Sites with private-subnet-only policies need an egress design covering all of those destinations before using this blueprint.

The firewall applies before Orca starts. Only loopback and enrolled Tailscale IPv4 addresses can reach TCP 6768. The host drops other inbound tailnet traffic. Pairing authenticates the client above that network boundary. Protect Tailscale enrollment, Orca offers, GitHub device codes, snapshots and shell logs as credentials.

## Publishing changes

Run the offline tests and inspect staged changes. Keep actual account inventories, device identifiers, operator logs, AWS CLI files, recovery metadata and pairing artifacts outside the repository and its history. Review release version and checksum changes against upstream publications. OS packages and Tailscale follow their configured repositories. A pinned AMI and checked application versions improve repeatability but a rebuild still depends on package availability.

Before publishing, review the author, committer, message, dates and trailers of every commit on the branch. Run Gitleaks against that history and inspect the tracked filenames. Ignoring a file only affects untracked copies. If a live credential has already reached another computer or remote, revoke or rotate it.

```sh
git log --format=fuller main
git ls-tree -r --name-only main
gitleaks git --redact --log-opts=main .
git bundle create ../orca-workstation-public.bundle refs/heads/main
git bundle verify ../orca-workstation-public.bundle
git clone --branch main ../orca-workstation-public.bundle ../orca-release-check
```

A branch-scoped bundle contains the selected branch's reachable Git objects. Use the reviewed bundle for file transfer, or push the reviewed `main` branch explicitly. An archive of the local working directory can also carry caches, local Git configuration, reflogs and filesystem metadata.
