import importlib.util
import json
import os
from pathlib import Path
import subprocess
import tempfile
import unittest

spec = importlib.util.spec_from_file_location('release', Path(__file__).with_name('prepare-desktop-release.py'))
release = importlib.util.module_from_spec(spec)
spec.loader.exec_module(release)


class ReleaseTests(unittest.TestCase):
    def test_version_rpc(self):
        result = {'organize': '3.3.0', 'engine': '0.2.0'}
        self.assertEqual(release.validate_version({'id': 'release-check', 'result': result}, '3.3.0'), result)

    def test_wrong_core_fails(self):
        with self.assertRaises(RuntimeError):
            release.validate_version({'id': 'release-check', 'result': {'organize': '2.0.0'}}, '3.3.0')

    def test_rpc_error_fails(self):
        with self.assertRaises(RuntimeError):
            release.validate_version({'id': 'release-check', 'error': {'message': 'failed'}}, '3.3.0')

    def test_wrong_request_fails(self):
        with self.assertRaises(RuntimeError):
            release.validate_version({'id': 'other', 'result': {'organize': '3.3.0'}}, '3.3.0')


class PublishTests(unittest.TestCase):
    """Exercise the publisher with fake tools; never call GitHub or upload files."""

    def run_publisher(self, **flags):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            scripts = root / 'scripts'
            scripts.mkdir()
            script = scripts / 'publish-desktop-release.sh'
            script.write_bytes(Path(__file__).with_name(script.name).read_bytes())
            output = root / 'build/desktop-release'
            output.mkdir(parents=True)
            sha = 'a' * 40
            (output / 'build-info.json').write_text(json.dumps({'commit': sha, 'appVersion': '0.1.0'}))
            (output / 'SHA256SUMS.txt').write_text('test checksum')
            (output / 'privacy-audit.json').write_text(json.dumps({'status': 'passed'}))
            tools = root / 'tools'
            tools.mkdir()
            stub = '''#!/usr/bin/env python3
import json, os, pathlib, sys
name = pathlib.Path(sys.argv[0]).name
args = sys.argv[1:]
if name == 'sha256sum':
    sys.exit(int(os.environ.get('MOCK_BAD_CHECKSUM', '0')))
if name == 'jq':
    print(json.loads(pathlib.Path(args[-1]).read_text())[args[1].lstrip('.')])
    sys.exit(0)
with open(os.environ['MOCK_LOG'], 'a') as log:
    log.write(json.dumps(args) + '\\n')
if args[:2] == ['release', 'view']:
    if os.environ.get('MOCK_EXISTS') != '1': sys.exit(1)
    value = os.environ.get('MOCK_PUBLISHED') != '1'
    print(json.dumps(value) if '--jq' in args else json.dumps({'isDraft': value}))
elif args[0] == 'api':
    print(os.environ.get('MOCK_HEAD', 'a' * 40))
elif args[:2] == ['release', 'upload']:
    sys.exit(int(os.environ.get('MOCK_UPLOAD_FAIL', '0')))
'''
            for name in ('gh', 'jq', 'sha256sum'):
                tool = tools / name
                tool.write_text(stub)
                tool.chmod(0o755)
            log = root / 'calls.jsonl'
            env = {**os.environ, 'PATH': str(tools) + os.pathsep + os.environ['PATH'],
                   'GH_REPO': 'test/organize', 'GITHUB_SHA': sha,
                   'GITHUB_RUN_NUMBER': '77', 'GITHUB_REF_NAME': 'main',
                   'GITHUB_STEP_SUMMARY': str(root / 'summary'), 'MOCK_LOG': str(log), **flags}
            result = subprocess.run(['bash', str(script)], env=env, capture_output=True, text=True)
            calls = [json.loads(line) for line in log.read_text().splitlines()] if log.exists() else []
            return result, calls

    def test_complete_upload_precedes_publication_and_sets_latest(self):
        result, calls = self.run_publisher()
        self.assertEqual(result.returncode, 0, result.stderr)
        create = next(c for c in calls if c[:2] == ['release', 'create'])
        self.assertIn('--draft', create)
        self.assertIn('--latest=false', create)
        upload = next(i for i, c in enumerate(calls) if c[:2] == ['release', 'upload'])
        edit = next(i for i, c in enumerate(calls) if c[:2] == ['release', 'edit'])
        self.assertLess(upload, edit)
        self.assertIn('--latest=true', calls[edit])

    def test_superseded_commit_does_not_replace_latest(self):
        result, calls = self.run_publisher(MOCK_HEAD='b' * 40)
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn('--latest=false', next(c for c in calls if c[:2] == ['release', 'edit']))

    def test_upload_failure_leaves_draft(self):
        result, calls = self.run_publisher(MOCK_UPLOAD_FAIL='1')
        self.assertNotEqual(result.returncode, 0)
        self.assertFalse(any(c[:2] == ['release', 'edit'] for c in calls))

    def test_published_rerun_does_not_overwrite_assets(self):
        result, calls = self.run_publisher(MOCK_EXISTS='1', MOCK_PUBLISHED='1')
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertFalse(any(c[:2] == ['release', 'upload'] for c in calls))

    def test_draft_rerun_resumes_upload(self):
        result, calls = self.run_publisher(MOCK_EXISTS='1')
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertFalse(any(c[:2] == ['release', 'create'] for c in calls))
        self.assertTrue(any(c[:2] == ['release', 'upload'] for c in calls))

    def test_wrong_branch_and_checksum_fail_before_github_mutations(self):
        for flags in ({'GITHUB_REF_NAME': 'feature'}, {'MOCK_BAD_CHECKSUM': '1'}):
            result, calls = self.run_publisher(**flags)
            self.assertNotEqual(result.returncode, 0)
            self.assertEqual(calls, [])


if __name__ == '__main__':
    unittest.main()
