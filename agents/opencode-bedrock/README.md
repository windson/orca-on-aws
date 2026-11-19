# OpenCode on Amazon Bedrock

OpenCode runs as the Orca service user and uses the EC2 instance role. The pinned Linux x86_64 release is v1.19.6. Its Bedrock provider selects Converse or Mantle according to each model's upstream adapter. The default for a new OpenCode configuration is `amazon-bedrock/openai.gpt-oss-20b-1:0`. Codex keeps its own default.

## Add to an existing Orca host

Use an AWS CLI profile with EC2 and IAM inspection, SSM Run Command and permission to manage the workstation role's named inline policy. The role should be dedicated to this workstation. Get the instance ID from your existing stack. Run from the repository root.

```sh
python3 tools/add_opencode.py --instance-id "$HOST_ID" --region us-east-1 --plan
python3 tools/add_opencode.py --instance-id "$HOST_ID" --region us-east-1
```

The installer checks the release checksum, installs the executable on Orca's PATH, configures the host user's Bedrock provider and verifies OpenCode can list models. It adds `OrcaOpenCodeBedrock` to the existing role. The policy covers regional inference, cross-region destinations when called through system inference profiles in the source region, and the regional Mantle project API. It grants no Marketplace subscription or IAM administration. Set `--bedrock-region` when EC2 and inference use different regions.

Fresh hosts can use `python3 tools/deploy.py --stack orca-opencode --agent opencode-bedrock --region us-east-1`. To create a host with both agents, deploy the reference's Codex default and run the add-on command above. Fresh hosts retain the Orca user's home. On legacy reference hosts, the installer places new OpenCode config, data and state on the retained workspace and preserves Orca's existing plugins and TUI settings.

## Choose a model

On the paired desktop or mobile client, select the AWS host and a project. Create an **OpenCode** chat. Open its model picker and select an `amazon-bedrock/…` entry. In an OpenCode terminal, use `/models`. Existing sessions can retain an explicit model.

The upstream catalog follows models.dev. The root-owned Linux managed configuration at `/etc/opencode/opencode.jsonc` enables only `amazon-bedrock`. OpenCode applies this setting after user and project settings. The entire Bedrock picker stays available, including models using Bedrock Runtime and Mantle. Model invocation depends on region, route, account entitlements and organization policies. Some models require an inference profile, a provider agreement or additional onboarding. Catalog refresh contacts a metadata service. Model inference uses AWS.

## Verify

In an interactive Session Manager shell on an existing host, run the following. Each inference check sends one short, billable prompt. On a fresh OpenCode-only host the scripts live in `/opt/orca-workstation/agent`.

```sh
user=$(systemctl show -p User --value orca-server)
sudo -Hu "$user" opencode models amazon-bedrock --refresh
sudo env ORCA_RUN_USER="$user" /opt/orca-workstation/addons/opencode-bedrock/verify.sh --inference
sudo env ORCA_RUN_USER="$user" /opt/orca-workstation/addons/opencode-bedrock/verify.sh --inference amazon-bedrock/openai.gpt-6.2-sol
sudo -Hu "$user" -- python3 /opt/orca-workstation/addons/opencode-bedrock/picker.py "$REGISTERED_CHECKOUT"
```

Set `REGISTERED_CHECKOUT` to an absolute project path registered with Orca. The picker check compares exact model IDs. For a client-level check, select OpenCode, start a new chat, request a one-word reply, then switch models in a second chat. If inference fails, inspect the provider error and verify that model's AWS route and access. To roll back the add-on, close OpenCode sessions and remove its managed executable link, managed provider file, and named inline role policy if this installation created them. Keep the user's data and sessions when rolling back.

[AWS setup walkthrough](https://aws.amazon.com/blogs/machine-learning/use-open-weight-models-as-your-ai-coding-agent-with-amazon-bedrock/) · [OpenCode release and checksums](https://github.com/anomalyco/opencode/releases/tag/v1.19.6) · [OpenCode source](https://github.com/anomalyco/opencode)
