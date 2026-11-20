# Kiro CLI

Kiro runs in a terminal on the Orca host. Kiro uses Amazon Bedrock for inference and authenticates the developer with a Kiro account. Model access, inference routing and usage are managed by Kiro. The module adds no inference permissions to the EC2 instance role. [Kiro data protection](https://kiro.dev/docs/privacy-and-security/data-protection/) · [Kiro models](https://kiro.dev/docs/models/)

## Install

For a new workstation, follow the main quickstart and pass `--agent kiro-cli` to the plan and deploy commands. For an existing Amazon Linux 2023 Orca host, run the following from a copy of this repository on the host as an administrator. The installer verifies the pinned Linux RPM checksum and Kiro signing key. [Quickstart](../../README.md) · [Kiro installation and signing key](https://kiro.dev/docs/getting-started/installation/)

```sh
sudo bash agents/kiro-cli/install.sh
run_user=$(systemctl show orca-server -p User --value)
sudo env ORCA_RUN_USER="$run_user" bash agents/kiro-cli/verify.sh
```

## Sign in and launch

1. Open a terminal in the remote Orca workspace. Run `kiro-cli login --use-device-flow` and complete the authorization in your browser. This puts the login on the computer where the agent runs. Use `kiro-cli whoami` in the same terminal to confirm. [Kiro authentication](https://kiro.dev/docs/getting-started/authentication/)
2. Choose **Kiro** as the workspace agent and open its **Terminal**. Orca 1.4.265 launches `kiro-cli chat --tui` and reports that Kiro has no structured chat session on this version.
3. To verify inference with your Kiro account, run `kiro-cli chat --no-interactive --trust-tools= 'Reply exactly KIRO_READY. Use no tools.'` from a trusted remote directory. This uses Kiro credits. The installation check itself runs offline after package download.
