"""Run after generate-license-bundle.py; tests never modify dependency caches."""
import hashlib
import importlib.util
import io
import json
from pathlib import Path
import tarfile
import tempfile
import unittest
from unittest.mock import patch
import zipfile

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location('license_bundle', ROOT / 'scripts/generate-license-bundle.py')
assert spec is not None and spec.loader is not None
bundle = importlib.util.module_from_spec(spec)
spec.loader.exec_module(bundle)


class LicenseBundleTests(unittest.TestCase):
    def test_all_reviewed_upstream_notices_match_cached_checksums(self):
        entries = json.loads((ROOT / 'legal/upstream.json').read_text())
        for key in entries:
            ecosystem, package = key.split(':', 1)
            name, version = package.rsplit('@', 1)
            with self.subTest(component=key):
                self.assertTrue(bundle.fallback_files(ecosystem, name, version))

    def test_manifest_matches_all_generated_files(self):
        root = ROOT / 'legal/generated'
        manifest = json.loads((root / 'manifest.json').read_text())
        for filename, expected in manifest['files'].items():
            self.assertEqual(hashlib.sha256((root / filename).read_bytes()).hexdigest(), expected, filename)
        self.assertEqual((root / 'LICENSE.txt').read_bytes(), (ROOT / 'LICENSE.txt').read_bytes())
        for p in manifest['components']:
            self.assertTrue(p['files'], p['name'])

    def test_exact_mpl_sources_are_available_offline(self):
        root = ROOT / 'legal/generated'
        manifest = json.loads((root / 'manifest.json').read_text())
        self.assertEqual({p['name'] for p in manifest['mplSources']}, bundle.MPL)
        with zipfile.ZipFile(root / 'MPL-SOURCES.zip') as archive:
            for p in manifest['mplSources']:
                data = archive.read(f'{p["name"]}-{p["version"]}.crate')
                self.assertEqual(hashlib.sha256(data).hexdigest(), p['sha256'])
                with tarfile.open(fileobj=io.BytesIO(data), mode='r:gz') as source:
                    self.assertTrue(any(m.name.endswith('Cargo.toml') for m in source.getmembers()))
                    self.assertTrue(any(m.name.endswith('.rs') for m in source.getmembers()))
            self.assertIn('Mozilla Public License Version 2.0', archive.read('MPL-2.0.txt').decode())

    def test_dual_licensed_gpl_alternative_is_allowed(self):
        self.assertFalse(bundle.forbidden_license('self_cell', 'Apache-2.0 OR GPL-2.0-only'))
        self.assertFalse(bundle.forbidden_license('r-efi', 'MIT OR Apache-2.0 OR LGPL-2.1-or-later'))
        self.assertFalse(bundle.forbidden_license('rawler', 'LGPL-2.1'))
        self.assertTrue(bundle.forbidden_license('krokiet', 'GPL-3.0-only'))
        self.assertTrue(bundle.forbidden_license('example', 'GPL-3.0-only'))
        self.assertTrue(bundle.forbidden_license('example', 'MIT AND GPL-2.0-only'))
        self.assertTrue(bundle.forbidden_license('example', 'GPL-2.0-only OR AGPL-3.0-only'))

    def test_missing_license_fails_closed(self):
        with self.assertRaisesRegex(RuntimeError, 'Missing license files'):
            bundle.fallback_files('test', 'unknown-component', '1.0')

    def test_changed_cached_license_fails_closed(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            (root / 'license.txt').write_text('altered')
            (root / 'upstream.json').write_text(json.dumps({'test:x@1': [
                {'file': 'license.txt', 'source': 'test', 'sha256': 'wrong'}]}))
            with patch.object(bundle, 'LEGAL', root):
                with self.assertRaisesRegex(RuntimeError, 'checksum mismatch'):
                    bundle.fallback_files('test', 'x', '1')


if __name__ == '__main__':
    unittest.main()
