# Seven days running Orca on AWS

The acceptance test was a new Orca reply over mobile data while the desktop slept. The phone passed that test. Over the week ending 20 November 2026, the workstation also had to survive a browser build, run a GPU-dependent SDK and preserve work across reconnects.

## Deployed workstation and fresh installations

| Area | Deployed workstation | Fresh reference installation |
| --- | --- | --- |
| Compute | `g5.2xlarge`, 8 vCPUs, 32 GiB RAM, one NVIDIA A10G in `us-east-1` | Version 0.2.0 defaults to the same capacity. Choose `--instance-type t3.large` when local workloads only need CPU. |
| Disk and recovery | Encrypted gp3, 30 GiB root and 150 GiB XFS workspace. AWS Backup selects the workspace daily with 14-day retention. | Same sizes and retention. The operator chooses the recovery point and credentials to preserve. The reference backup schedule is 05:00 UTC. |
| Devices | Desktop via a Session Manager port forward. Mobile reaches the EC2 Tailscale address, including on mobile data. The EC2 security group has zero inbound rules. | Desktop can use either private route. Mobile needs its own Tailscale enrollment, firewall entry and pairing offer. |
| Agents | Orca Server 1.4.265, Codex 0.168.0, OpenCode 1.19.6 and Kiro CLI 3.5.0 on one host. Codex defaults to GPT-6.2 Sol. | The deployer installs one agent profile. Use the OpenCode add-on and the Kiro installation guide to assemble the same lineup on a Codex host. Kiro requires a separate sign-in. |
| Privileges | The operator selected Codex Full access, used project-level SDK environments and authorized project-specific AWS access. The OS audit found no general sudo grant for the Orca user. | Codex starts with workspace write access and approvals on request. Each agent module declares its own inference permissions. The operator supplies any additional project permissions. |

EC2 inventory, attached volumes, backup selection, service status, driver and binary versions were checked on 20 November. The GPU calculation, cellular test and incidents below are observations from the deployment week. [Pairing guide](access.md) · [Operations and recovery](operations.md)

## 13 November · Pick the runtime and test the route

Long-running shells, Git worktrees, build tools and an Orca server needed one Linux environment that clients could repeatedly reconnect to. EC2 provided that environment. The agent calls Bedrock for model inference. We compared regional model discovery on the endpoint Codex actually uses, moved compute and inference to Northern Virginia, and removed the earlier test deployment. A model picker can be stale. A fresh reply using the workstation's instance role is the check to repeat in a new account.

Pairing exposed a second distinction. A loopback address works on the desktop while its SSM tunnel is alive. A mobile offer containing the same address sends the phone back to itself. Direct EC2 pairing over Tailscale gave the phone an independent path without opening the EC2 security group. WebSocket close code 1006 alone does not identify which hop failed.

## 13–16 November · Find what actually went offline

One confirmed outage started when the 2 GiB host exhausted memory and swap while browser and agent processes were running. A child process died and the Orca service stopped. After the server restarted, the desktop tunnel still listened locally but failed its WebSocket handshake. These were separate faults. We reserved memory for host services, moved temporary files onto disk, increased host memory and checked the tunnel with a handshake. The phone acceptance test used cellular data with the laptop asleep. A successful QR scan had only proved enrollment.

## 19 November · A project SDK changed the hardware requirement

Our goal was a cloud version of a development laptop. The first CPU workstation could ask Bedrock for a model response. Then a project SDK needed CUDA on the same machine as its checkout, dependencies and terminal. Asking Bedrock for a larger model would still leave that SDK without a GPU. We chose G5 so development could continue entirely on EC2. In an Orca terminal, CUDA-enabled PyTorch on the A10G summed the squares of the integers 0 through 15 and returned `1240`. A native Codex subprocess can run in a different service scope and needs its own GPU test.

The running machine had outgrown its original CloudFormation parameters. On 20 November the older stack still declared a `t3.large` with a 16 GiB root and 30 GiB workspace. EC2 reported the GPU and 30/150 GiB disks above. Inspect both the stack and the attached resources before planning maintenance on an existing machine. The fresh-stack quickstart creates a new workstation.

We verified GPT-6.2 Sol and Astra with fresh inferences and set Sol as the Codex default. OpenCode used its own Bedrock provider and exposed a different picker. Model visibility, invocation rights and context limits are separate checks. [Codex on Bedrock](../agents/codex-bedrock/README.md) · [OpenCode on Bedrock](../agents/opencode-bedrock/README.md)

### Why two kinds of permission had to change

OpenCode needed Bedrock operations and inference profiles beyond those used by the original Codex agent. Updating the EC2 instance role let the new agent use temporary AWS credentials for those calls. Project deployments also needed their own AWS authority. We delegated that work separately so an ordinary model call and a project release could have different permissions. The reference builds the host role from the selected agent and keeps backup operations on a separate AWS Backup role.

The SDK faced a different obstacle. A process can have permission to invoke Bedrock and still be unable to write its environment or open a GPU device. An administrator installed the NVIDIA driver and made the necessary devices available to the Orca service. The unprivileged process could then install project dependencies in a writable virtual environment and run the CUDA check. The operator could choose automatic tool approval for a trusted session while Linux permissions and AWS policies still governed each command. [Permission design and verification](security.md#which-permission-to-change)

## 20 November · Put fixes on the computer that owns the work

Updating the desktop app exposed a bot picker before the remote runtime advertised bot creation. We updated and checked the Linux server's capability. Opening a child worktree exposed an inherited path the Orca service user could not traverse. Routing new worktrees to a writable retained location preserved existing checkouts. For empty projects, Orca also needed a Git author on the remote host to make the first commit.

Kiro surfaced the same ownership issue in a different place. A browser could approve the device while the CLI failed its sign-in because its registration store was read-only inside the service. Checking the service user's filesystem view explained the apparent contradiction. Keep the credential store writable by that user on encrypted storage, and decide who can restore its backups before approving the cloud device. [Kiro sign-in and tool permissions](../agents/kiro-cli/README.md) · [Worktrees and Git setup](workspaces.md)
