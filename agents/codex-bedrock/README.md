# Codex on Amazon Bedrock

The module installs `@openai/codex@0.168.0` and selects the native `amazon-bedrock` provider. The EC2 instance role signs requests. Configure access to the OpenAI models you intend to use in the Bedrock inference region. In particular, the `openai.gpt-6.2-sol` default must be available to your account. [Sol model card](https://docs.aws.amazon.com/bedrock/latest/userguide/model-card-openai-gpt-6-2-sol.html) · [Astra model card](https://docs.aws.amazon.com/bedrock/latest/userguide/model-card-openai-gpt-6-2-astra.html)

| Setting | Fresh workspace |
| --- | --- |
| Default model | GPT-6.2 Sol, `openai.gpt-6.2-sol` |
| Reasoning and service tier | `xhigh`, `default` (Standard) |
| Inference region | `us-east-1` |
| Orca account and permissions | System account, Own settings |
| Codex permissions | `workspace-write`, approvals on request |

Use `--parameter BedrockRegion=<region>` to change inference residency independently of `--region` for EC2. The IAM policy and fresh Codex config both use this value. `configure.py` reads metadata from the pinned CLI binary, selects nine existing model entries, and adds GPT-6.2 Sol and GPT-6.2 Astra for Orca's picker. Model availability and supported tiers depend on the account and region. Review the adapter when changing the CLI version.

## First chat

1. From an administrative SSM session run `sudo /opt/orca-workstation/agent/verify.sh --inference`. It launches a fresh Codex process as the service user, uses the configured default and checks the actual reply.
2. Open a shell with `sudo -iu orca`. Place a trusted Git checkout under `/workspace/projects`. For an empty first project, run the following.

   ```sh
   git init -b main /workspace/projects/hello
   orca-host repo add --kind git --path /workspace/projects/hello --json
   ```

3. In the paired client select the remote host and the project. Open a **new Codex chat**, check the selected model and send a short prompt. On a phone, confirm that you can see the reply while the desktop is asleep.

Settings are stored in `/workspace/home/.codex/config.toml`. Restoring a snapshot preserves this file and its model catalog. If the restored workspace used a different Bedrock region, update that config as the service user and check that it matches the new stack's agent policy.

[Optional workspace setup and GitHub integration](../../docs/workspaces.md)
