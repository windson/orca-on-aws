# Coding agent modules

Each deployment selects one module with `--agent`. The shared AWS and Orca layers own the machine, access paths and workspace. Each module owns its provider policy, CLI installation, settings and verification.

| Module | Status |
| --- | --- |
| [codex-bedrock](codex-bedrock/README.md) | Implemented |
| [kiro-cli](kiro-cli/README.md) | Planned |
| [claude-code-bedrock](claude-code-bedrock/README.md) | Planned |

## Add a module

1. Create `agents/<name>/agent.json`. Use the Codex manifest as the schema example. Declare CloudFormation `parameters`, `outputs`, managed `policies`, the allowlisted module `files`, and ordered `installArgs`. Each argument must resolve to one line. Pass module parameters to deploy with repeated `--parameter KEY=VALUE` options.
2. Supply `install.sh`, `activate.sh`, and `verify.sh`. The renderer installs the listed files under `/opt/orca-workstation/agent/`. Bootstrap calls the installer as root and passes its declared argument values. Write user configuration as the `orca` account under its retained home. Keep provider credentials out of the template.
3. Verify local installation without billing or device interaction. Fresh workspaces then run `activate.sh` to select the system account and configure the agent in Orca. Restores preserve the owner's existing Orca preferences. Provide an explicit inference check for providers that bill by usage.
4. Document model access, region selection, versions and client setup. Add tests for template composition, config ownership and preservation, and a live smoke procedure. Only add a runnable manifest when the installer and checks exist.

The two planned integrations have no manifests. They are absent from deploy's choices until implemented.
