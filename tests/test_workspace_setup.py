"""Exercise repository discovery without network access or package installation."""
import json
import os
import pathlib
import subprocess
import tempfile
import unittest

SCRIPT = pathlib.Path(__file__).resolve().parents[1] / 'platform/orca/setup-workspace.sh'


class SetupDiscoveryTests(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory(prefix='orca-setup-test-')
        self.addCleanup(self.temporary.cleanup)
        self.repo = pathlib.Path(self.temporary.name)
        subprocess.run(['git', 'init', '-q', str(self.repo)], check=True)

    def write(self, name, content=''):
        path = self.repo / name
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(content)

    def run_plan(self, *args):
        subprocess.run(['git', '-C', str(self.repo), 'add', '.'], check=True)
        return subprocess.run(['bash', str(SCRIPT), '--dry-run', *args],
                              cwd=self.repo, text=True, capture_output=True)

    def test_python_and_arbitrary_frontend_directory(self):
        self.write('pyproject.toml', '[project]\nname="different-project"\nrequires-python=">=3.13"\n')
        self.write('uv.lock')
        self.write('ui/package.json', '{"scripts":{"build":"vite build"}}')
        self.write('ui/package-lock.json', '{}')
        result = self.run_plan()
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertNotIn(str(self.repo), result.stdout)
        actions = json.loads(result.stdout)['actions']
        self.assertEqual([(a['directory'], a['manager']) for a in actions], [('.', 'uv'), ('ui', 'npm')])
        self.assertNotIn('--python', actions[0]['commands'][0])
        self.assertEqual(len(actions[1]['commands']), 1, 'Building must be opt-in')
        built = json.loads(self.run_plan('--build').stdout)['actions']
        self.assertEqual(built[1]['commands'][-1], ['npm', 'run', 'build'])
        self.assertFalse((self.repo / '.venv').exists(), 'Dry run must not install dependencies')

    def test_package_managers_and_deep_fixture_scope(self):
        self.write('package.json', '{"packageManager":"pnpm@10.0.0"}')
        self.write('pnpm-lock.yaml', "lockfileVersion: '9.0'\n")
        self.write('classic/package.json', '{}')
        self.write('classic/yarn.lock', '# yarn lockfile v1\n')
        self.write('modern/package.json', '{}')
        self.write('modern/yarn.lock', '__metadata:\n  version: 8\n')
        self.write('tests/fixture/package.json', '{}')
        self.write('tests/fixture/package-lock.json', '{}')
        result = self.run_plan()
        self.assertEqual(result.returncode, 0, result.stderr)
        actions = json.loads(result.stdout)['actions']
        self.assertEqual([a['directory'] for a in actions], ['.', 'classic', 'modern'])
        self.assertIn('--frozen-lockfile', actions[0]['commands'][0])
        self.assertIn('--frozen-lockfile', actions[1]['commands'][0])
        self.assertIn('--immutable', actions[2]['commands'][0])
        selected = json.loads(self.run_plan('--directory', 'tests/fixture').stdout)['actions']
        self.assertEqual([a['directory'] for a in selected], ['tests/fixture'])

    def test_conflicting_lockfiles_fail_before_install(self):
        self.write('package.json', '{}')
        self.write('package-lock.json', '{}')
        self.write('pnpm-lock.yaml')
        result = self.run_plan()
        self.assertNotEqual(result.returncode, 0)
        self.assertIn('Choose one JavaScript lockfile', result.stderr)

    def test_shared_environment_symlink_is_rejected(self):
        self.write('pyproject.toml')
        self.write('uv.lock')
        (self.repo / '.venv').symlink_to('/tmp')
        result = self.run_plan()
        self.assertNotEqual(result.returncode, 0)
        self.assertIn('Refusing a shared', result.stderr)

    def test_directory_cannot_escape_checkout(self):
        result = self.run_plan('--directory', '..')
        self.assertNotEqual(result.returncode, 0)
        self.assertIn('inside this checkout', result.stderr)

    def run_with_fake_manager(self, manager, version):
        home = self.repo / 'fake-home'
        binary = home / '.local/bin' / manager
        binary.parent.mkdir(parents=True)
        binary.write_text('#!/bin/sh\nif [ "$1" = "--version" ]; then echo ' + version
                          + '; else touch "$HOME/install-was-run"; fi\n')
        binary.chmod(0o755)
        subprocess.run(['git', '-C', str(self.repo), 'add', '.'], check=True)
        result = subprocess.run(['bash', str(SCRIPT)], cwd=self.repo,
            env=dict(os.environ, HOME=str(home)), text=True, capture_output=True)
        self.assertFalse((home / 'install-was-run').exists(), 'Incompatible manager must not install')
        return result

    def test_classic_yarn_cannot_install_modern_lockfile(self):
        self.write('package.json', '{}')
        self.write('yarn.lock', '__metadata:\n  version: 8\n')
        result = self.run_with_fake_manager('yarn', '1.22.22')
        self.assertNotEqual(result.returncode, 0)
        self.assertIn('Yarn major does not match', result.stderr)

    def test_declared_package_manager_version_is_enforced(self):
        self.write('package.json', '{"packageManager":"pnpm@10.0.0"}')
        self.write('pnpm-lock.yaml', "lockfileVersion: '9.0'\n")
        result = self.run_with_fake_manager('pnpm', '9.15.0')
        self.assertNotEqual(result.returncode, 0)
        self.assertIn('packageManager requires 10.0.0', result.stderr)


if __name__ == '__main__':
    unittest.main()
