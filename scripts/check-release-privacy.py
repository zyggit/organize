"""Fail closed on local data and recognizable secrets, without printing values.

Run on tracked source before building and on the real bundle before staging.
Frozen Python modules and nested ZIP/crate archives are inspected decompressed.
This is defense in depth, not proof that arbitrary unknown secrets cannot exist.
"""
import argparse
import io
import json
from pathlib import Path, PurePosixPath
import re
import subprocess
import tarfile
import zipfile

ROOT = Path(__file__).resolve().parents[1]
RULES = {
    'personal-home-path': rb'(?:\x2fUsers\x2f(?!runner(?:\x2f|\x00))[^/\s\x00"\'<>]+/|\x2fhome\x2f(?!runner(?:\x2f|\x00))[^/\s\x00"\'<>]+/|[A-Za-z]:\\Users\\(?!runner\\)[^\\\s\x00"\'<>]+\\)',
    'github-token': rb'(?:gh[pousr]_[A-Za-z0-9]{36,}|github_pat_[A-Za-z0-9_]{40,})',
    'aws-access-key': rb'(?:AKIA|ASIA)[A-Z0-9]{16}',
    'openai-key': rb'sk-(?:proj-|svcacct-)?[A-Za-z0-9_-]{40,}',
    'private-key': rb'-----BEGIN (?:RSA |EC |DSA |OPENSSH |ENCRYPTED )?PRIVATE KEY-----[\r\n]+[A-Za-z0-9+/=\r\n]{100,}-----END (?:RSA |EC |DSA |OPENSSH |ENCRYPTED )?PRIVATE KEY-----',
}
PATTERNS = {name: re.compile(pattern) for name, pattern in RULES.items()}
FORBIDDEN_DIRS = {'.git', '.ssh', '.aws', '.codex', '.DS_Store', '__MACOSX'}
FORBIDDEN_SUFFIXES = {'.db', '.sqlite', '.sqlite3', '.log', '.p12', '.pfx', '.key'}


def check_name(name):
    path = PurePosixPath(name)
    if path.is_absolute() or '..' in path.parts:
        raise RuntimeError('Privacy audit failed: unsafe archive path')
    if any(part in FORBIDDEN_DIRS or part == '.env' or part.startswith('.env.') for part in path.parts):
        raise RuntimeError('Privacy audit failed: forbidden data/config entry')
    if path.suffix.lower() in FORBIDDEN_SUFFIXES:
        raise RuntimeError('Privacy audit failed: runtime data or private credential file')


def inspect_blob(name, data, depth=0):
    check_name(name)
    for rule, pattern in PATTERNS.items():
        if pattern.search(data):
            # Never echo matching bytes, source lines, or private absolute paths.
            raise RuntimeError(f'Privacy audit failed: {rule}')
    count = 1
    if depth >= 5:
        raise RuntimeError('Privacy audit failed: archive nesting limit')
    if data.startswith(b'PK\x03\x04'):
        with zipfile.ZipFile(io.BytesIO(data)) as archive:
            for item in archive.infolist():
                if not item.is_dir():
                    if item.file_size > 256 * 1024 * 1024:
                        raise RuntimeError('Privacy audit failed: oversized archive entry')
                    count += inspect_blob(item.filename, archive.read(item), depth + 1)
    elif name.endswith(('.crate', '.tar.gz', '.tgz')):
        with tarfile.open(fileobj=io.BytesIO(data), mode='r:*') as archive:
            for item in archive.getmembers():
                check_name(item.name)
                if item.issym() or item.islnk():
                    raise RuntimeError('Privacy audit failed: archive link')
                if item.isfile():
                    if item.size > 256 * 1024 * 1024:
                        raise RuntimeError('Privacy audit failed: oversized archive entry')
                    count += inspect_blob(item.name, archive.extractfile(item).read(), depth + 1)
    return count


def audit_source():
    files = subprocess.check_output(['git', 'ls-files', '-z'], cwd=ROOT).decode().split('\x00')
    count = 0
    for name in files:
        if not name:
            continue
        path = ROOT / name
        if path.is_symlink():
            raise RuntimeError('Privacy audit failed: tracked source symlink')
        count += inspect_blob(name, path.read_bytes())
    return {'status': 'passed', 'sourceEntriesScanned': count, 'rules': sorted(RULES)}


def audit_app(app):
    from PyInstaller.archive.readers import CArchiveReader
    count = 0
    for path in app.rglob('*'):
        if path.is_symlink():
            if not path.resolve().is_relative_to(app.resolve()):
                raise RuntimeError('Privacy audit failed: external bundle symlink')
        elif path.is_file():
            count += inspect_blob(str(path.relative_to(app)), path.read_bytes())
    engine = CArchiveReader(str(app / 'Contents/MacOS/organize-engine'))
    for name, entry in engine.toc.items():
        if entry[-1] == 'z':
            archive = engine.open_embedded_archive(name)
            for module in archive.toc:
                data = archive.extract(module, raw=True)
                if data is not None:
                    count += inspect_blob(module, data)
        else:
            count += inspect_blob(name, engine.extract(name))
    return {'status': 'passed', 'bundleEntriesScanned': count,
            'frozenPythonArchiveInspected': True, 'rules': sorted(RULES),
            'method': 'clean CI build; data-file denylist; decompressed secret/path scan'}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--source', action='store_true')
    args = parser.parse_args()
    if not args.source:
        parser.error('Use --source; bundle audit is called by prepare-desktop-release.py')
    print(json.dumps(audit_source(), sort_keys=True))


if __name__ == '__main__':
    main()
