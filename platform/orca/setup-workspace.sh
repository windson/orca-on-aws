#!/bin/bash
# Install dependencies selected by each checkout's lockfiles; no project names.
set -euo pipefail
exec python3 - "$@" <<'PY'
import argparse
import fcntl
import json
import os
from pathlib import Path
import shlex
import shutil
import subprocess
import sys
import time

parser = argparse.ArgumentParser(description='Set up an Orca Git worktree from its lockfiles.')
parser.add_argument('--dry-run', action='store_true', help='Print the plan without installing anything')
parser.add_argument('--build', action='store_true', help='Also run each detected package.json build script')
parser.add_argument('--directory', action='append', help='Explicit project directory; repeat for monorepos')
args = parser.parse_args()
if os.geteuid() == 0:
    sys.exit('Run workspace setup as an ordinary user, not root.')

root = Path(subprocess.check_output(['git', 'rev-parse', '--show-toplevel'], text=True).strip()).resolve()
lock_names = {'uv.lock', 'package-lock.json', 'npm-shrinkwrap.json', 'pnpm-lock.yaml', 'yarn.lock'}
if args.directory:
    directories = set(args.directory)
else:
    # Limit discovery to the root and immediate children. Deep example/fixture
    # projects are not automatically installed; select deeper roots explicitly.
    tracked = subprocess.check_output(['git', '-C', str(root), 'ls-files', '-z']).decode().split('\0')
    directories = {str(Path(name).parent) for name in tracked if name
                   and Path(name).name in lock_names and len(Path(name).parts) <= 2}

actions = []
for relative in sorted(directories):
    directory = (root / relative).resolve()
    if not directory.is_relative_to(root) or not directory.is_dir():
        sys.exit('Project directory must be inside this checkout.')
    relative = str(directory.relative_to(root))
    for name in lock_names | {'pyproject.toml', 'package.json', '.venv', 'node_modules'}:
        if (directory / name).is_symlink():
            sys.exit('Refusing a shared manifest/environment symlink: ' + str(Path(relative) / name))

    if (directory / 'uv.lock').is_file():
        if not (directory / 'pyproject.toml').is_file():
            sys.exit('uv.lock requires pyproject.toml in ' + relative)
        # uv selects Python from .python-version / requires-python.
        actions.append({'directory': relative, 'manager': 'uv',
                        'commands': [['uv', 'sync', '--locked', '--dev']]})

    javascript_locks = [name for name in lock_names - {'uv.lock'} if (directory / name).is_file()]
    if not javascript_locks:
        continue
    if len(javascript_locks) != 1:
        sys.exit('Choose one JavaScript lockfile in ' + relative + ': ' + ', '.join(sorted(javascript_locks)))
    manifest = directory / 'package.json'
    if not manifest.is_file():
        sys.exit('JavaScript lockfile requires package.json in ' + relative)
    package = json.loads(manifest.read_text())
    lock = javascript_locks[0]
    if lock in {'package-lock.json', 'npm-shrinkwrap.json'}:
        manager, install = 'npm', ['npm', 'ci', '--include=dev', '--no-audit', '--no-fund']
    elif lock == 'pnpm-lock.yaml':
        manager, install = 'pnpm', ['pnpm', 'install', '--frozen-lockfile', '--prod=false']
    else:
        manager = 'yarn'
        contents = (directory / lock).read_text()[:8192]
        if '# yarn lockfile v1' in contents:
            install = ['yarn', 'install', '--frozen-lockfile', '--production=false']
        elif '__metadata:' in contents:
            install = ['yarn', 'install', '--immutable']
        else:
            sys.exit('Unrecognized Yarn lockfile format in ' + relative)
    declared = package.get('packageManager', '')
    declared_manager = declared.split('@')[0]
    if declared_manager and declared_manager != manager:
        sys.exit('packageManager conflicts with the lockfile in ' + relative)
    commands = [install]
    if args.build and package.get('scripts', {}).get('build'):
        commands.append([manager, 'run', 'build'])
    actions.append({'directory': relative, 'manager': manager, 'commands': commands,
                    'requiredVersion': declared.split('@', 1)[1].split('+', 1)[0] if '@' in declared else None})

print(json.dumps({'checkout': '.', 'buildRequested': args.build, 'actions': actions}, indent=2), flush=True)
if args.dry_run:
    sys.exit(0)
if not actions:
    print('No supported lockfiles found. Configure a repository-specific command if setup is needed.')
    sys.exit(0)

environment = dict(os.environ)
environment['PATH'] = str(Path.home() / '.local/bin') + ':/usr/local/bin:/usr/bin:/bin:' + environment.get('PATH', '')
missing = sorted({action['manager'] for action in actions
                  if not shutil.which(action['manager'], path=environment['PATH'])})
if missing:
    sys.exit('Install the package manager required by this repository before setup: ' + ', '.join(missing))
for action in actions:
    if action['manager'] == 'uv':
        continue
    version = subprocess.check_output([action['manager'], '--version'],
        cwd=root / action['directory'], env=environment, text=True).strip()
    required = action.get('requiredVersion')
    if required and version != required:
        sys.exit(action['manager'] + ' version mismatch in ' + action['directory']
                 + ': packageManager requires ' + required + ', installed ' + version)
    if action['manager'] == 'yarn':
        classic_lock = '--frozen-lockfile' in action['commands'][0]
        try:
            classic_binary = int(version.split('.')[0]) < 2
        except ValueError:
            sys.exit('Cannot determine installed Yarn major version.')
        if classic_lock != classic_binary:
            sys.exit('Installed Yarn major does not match the lockfile in ' + action['directory'])
os.umask(0o077)
cache = Path.home() / '.cache'
temporary = cache / 'orca-tmp'
temporary.mkdir(parents=True, mode=0o700, exist_ok=True)
temporary.chmod(0o700)
environment.update(TMPDIR=str(temporary), UV_NO_PROGRESS='1', UV_CONCURRENT_BUILDS='1', UV_LINK_MODE='copy')
environment.setdefault('NODE_OPTIONS', '--max-old-space-size=768')

# Bound concurrent builds on the small EC2 host; package extraction uses disk.
with (cache / 'orca-workspace-setup.lock').open('a') as lock:
    print('Waiting for the workspace setup slot...', flush=True)
    deadline = time.monotonic() + 1800
    while True:
        try:
            fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
            break
        except BlockingIOError:
            if time.monotonic() >= deadline:
                sys.exit('Timed out waiting for another setup to finish.')
            time.sleep(1)
    for action in actions:
        directory = root / action['directory']
        step_environment = dict(environment)
        if action['manager'] == 'uv':
            step_environment['UV_PROJECT_ENVIRONMENT'] = str(directory / '.venv')
        for command in action['commands']:
            print('[' + action['directory'] + '] ' + shlex.join(command), flush=True)
            result = subprocess.run(command, cwd=directory, env=step_environment)
            if result.returncode:
                sys.exit('Workspace setup failed in ' + action['directory'] + ' (exit ' + str(result.returncode) + ').')
print('ORCA_WORKSPACE_SETUP_OK', flush=True)
PY
