# Optional workspace setup and GitHub integration

For trusted repositories, set Orca's **Automate workspace setup** command to `/opt/orca-workstation/orca/setup-workspace.sh`. The hook finds tracked lockfiles at the root and one level below. It supports npm, pnpm, Yarn and uv, and checks the selected package manager's version when declared. Preview it inside the checkout with `--dry-run`. Install the matching project tools as needed. Dependency installation can execute repository code.

To enable GitHub pull requests and checks on the **remote** provider, run these commands in an interactive SSM session. Complete GitHub's device login in your own browser. In Orca, select this host under **Settings → Integrations** and choose **Re-check**.

```sh
sudo /opt/orca-workstation/github/install.sh
sudo -iu orca gh auth login --hostname github.com --git-protocol https --web
sudo -iu orca gh auth status --hostname github.com
```

GitHub CLI stores the session in the service user's retained home when using its file credential store. Protect workspace backups accordingly.
