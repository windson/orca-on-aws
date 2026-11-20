# Orca worktrees, workspace setup and GitHub integration

## Create a project from an empty folder

Orca initializes the repository and makes an empty `Initial commit`. Before using **Create a new project**, set the author once in an Orca terminal on the host that will own the project. Use the name and email you want recorded in future commits. For GitHub privacy, use the no-reply address shown in your GitHub email settings.

```sh
git config --global user.name "Your chosen commit name"
git config --global user.email "Your chosen commit email"
(cd /tmp && git var GIT_AUTHOR_IDENT && git var GIT_COMMITTER_IDENT)
```

If Orca reports **Git author identity is not configured**, return to the dialog and click **Create project** after setting both values. GitHub sign-in authenticates repository access. Git reads the author of the first commit from the remote user's Git configuration, before the new repository has any settings of its own.

## Where child worktrees are created

On a fresh host, Orca creates worktrees under the service user's retained home at
`/workspace/home/orca/workspaces`. With Orca's nested layout, each project gets
its own directory. A project's explicit worktree location takes precedence.

If **Parent & Children → New Child Worktree** reports `EACCES` during **Set up
workspace**, check the path in the error. A restored profile can still point at
`/home/ec2-user/orca/workspaces` even though Orca now runs as a different user.
All projects that inherit that directory are affected. The error occurs before
the dependency setup hook or coding agent starts.

At service startup, the [worktree directory helper](../platform/orca/prepare-worktrees.py)
tests the default directory as the service user. For the inaccessible legacy
default, it uses Orca's offline export, preserves the prior layout in history,
and sets the new default on the retained disk. The service imports the edited
profile at startup. The previous settings are in a private
`before-worktree-root-*` file alongside the profile, and Orca archives the
original SQLite state during export. Existing checkouts keep their locations.

On an older deployment, finish active jobs, stop the Orca service and run the
helper as its Unix user with `ORCA_USER_DATA_PATH` pointing to the server's state.
Pass an absolute directory on the retained volume that the systemd service can
write to. Start Orca and create a child from a project that inherits the default.
If only one project fails, inspect its **worktree base path** override before
changing the host setting.

## Dependency setup

For trusted repositories, set Orca's **Automate workspace setup** command to `/opt/orca-workstation/orca/setup-workspace.sh`. The hook finds tracked lockfiles at the root and one level below. It supports npm, pnpm, Yarn and uv, and checks the selected package manager's version when declared. Preview it inside the checkout with `--dry-run`. Install the matching project tools as needed. Dependency installation can execute repository code.

## GitHub integration

To enable GitHub pull requests and checks on the **remote** provider, run these commands in an interactive SSM session. Complete GitHub's device login in your own browser. In Orca, select this host under **Settings → Integrations** and choose **Re-check**.

```sh
sudo /opt/orca-workstation/github/install.sh
sudo -iu orca gh auth login --hostname github.com --git-protocol https --web
sudo -iu orca gh auth status --hostname github.com
```

GitHub CLI stores the session in the service user's retained home when using its file credential store. Protect workspace backups accordingly.
