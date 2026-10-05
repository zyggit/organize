import importlib.util
import io
from pathlib import Path
import tarfile
import unittest
import zipfile

spec = importlib.util.spec_from_file_location('privacy', Path(__file__).with_name('check-release-privacy.py'))
assert spec is not None and spec.loader is not None
privacy = importlib.util.module_from_spec(spec)
spec.loader.exec_module(privacy)


class PrivacyTests(unittest.TestCase):
    def test_personal_path_fails_without_echoing_it(self):
        private = b'/Users/' + b'private-user/Documents/example.txt'
        with self.assertRaisesRegex(RuntimeError, '^Privacy audit failed: personal-home-path$'):
            privacy.inspect_blob('module.pyc', private)

    def test_ci_runner_path_is_not_a_personal_path(self):
        self.assertEqual(privacy.inspect_blob('module.pyc', b'/Users/runner/work/organize/code.py'), 1)

    def test_documentation_placeholder_is_not_a_real_windows_username(self):
        self.assertEqual(privacy.inspect_blob('module.pyc', b'C:\\Users\\<username>\\AppData'), 1)
        with self.assertRaisesRegex(RuntimeError, 'personal-home-path'):
            privacy.inspect_blob('module.pyc', b'C:\\Users\\private-user\\AppData')

    def test_tokens_fail(self):
        for secret in [b'ghp_' + b'A' * 36, b'AKIA' + b'A' * 16, b'sk-proj-' + b'B' * 50]:
            with self.assertRaises(RuntimeError):
                privacy.inspect_blob('resource', secret)

    def test_frozen_diagnostic_does_not_echo_secret_or_private_entry_path(self):
        secret = b'sk-proj-' + b'B' * 50
        private_name = '/Users/' + 'private-user/file'
        with self.assertRaises(RuntimeError) as caught:
            privacy.inspect_frozen_entry(private_name, secret)
        self.assertNotIn(private_name, str(caught.exception))
        self.assertNotIn(secret.decode(), str(caught.exception))
        self.assertIn('<redacted entry>', str(caught.exception))

    def test_data_files_and_traversal_fail(self):
        for name in ['journal.db', 'diagnostic.log', '.env', '.ssh/id_rsa', '../private', 'signing.p12']:
            with self.assertRaises(RuntimeError):
                privacy.inspect_blob(name, b'data')

    def test_nested_zip_is_decompressed_before_checking(self):
        archive = io.BytesIO()
        with zipfile.ZipFile(archive, 'w', compression=zipfile.ZIP_DEFLATED) as z:
            z.writestr('module.pyc', b'ghp_' + b'A' * 36)
        with self.assertRaises(RuntimeError):
            privacy.inspect_blob('library.zip', archive.getvalue())

    def test_archive_hardlink_must_target_an_internal_scanned_file(self):
        def archive(target, data=b'TZif'):
            stream = io.BytesIO()
            with tarfile.open(fileobj=stream, mode='w:gz') as tar:
                file = tarfile.TarInfo('UTC')
                file.size = len(data)
                tar.addfile(file, io.BytesIO(data))
                link = tarfile.TarInfo('GMT')
                link.type = tarfile.LNKTYPE
                link.linkname = target
                tar.addfile(link)
            return stream.getvalue()
        self.assertGreater(privacy.inspect_blob('zoneinfo.tar.gz', archive('UTC')), 1)
        for target in ['/private/file', '../file', 'missing']:
            with self.assertRaises(RuntimeError):
                privacy.inspect_blob('zoneinfo.tar.gz', archive(target))
        with self.assertRaises(RuntimeError):
            privacy.inspect_blob('zoneinfo.tar.gz', archive('UTC', b'ghp_' + b'A' * 36))

    def test_public_license_attribution_is_allowed(self):
        self.assertEqual(privacy.inspect_blob('LICENSE.txt', b'Copyright Example <author@example.org>'), 1)


if __name__ == '__main__':
    unittest.main()
