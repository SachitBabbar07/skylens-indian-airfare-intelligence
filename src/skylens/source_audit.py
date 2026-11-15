"""Reproduce pinned public-archive audits in isolated storage, never training.

No source search, browser automation, credentials, conversion or model fitting.
Network access is opt-in; only the reviewed Kaggle archive endpoint is allowed.
"""
from __future__ import annotations

import argparse
import hashlib
import io
import json
import re
import stat
import urllib.request
import zipfile
from pathlib import Path, PurePosixPath

MAX_ARCHIVE = 32_000_000
MAX_EXPANDED = 200_000_000
LICENSES = {'CC0: Public Domain', 'Database: Open Database, Contents: Database Contents'}


def sha256(content: bytes) -> str:
    return hashlib.sha256(content).hexdigest()


def validate_spec(spec: dict) -> None:
    if (spec.get('role') != 'audit_only_not_training' or spec.get('training_eligible') is not False
            or spec.get('declared_license') not in LICENSES
            or not re.fullmatch(r'[a-z0-9_-]+/[a-z0-9_-]+', spec.get('source', ''))
            or type(spec.get('version')) is not int or spec['version'] < 1):
        raise ValueError('Only reviewed, explicitly audit-only public archives are supported')
    expected = ('https://www.kaggle.com/api/v1/datasets/download/' + spec['source']
                + '?datasetVersionNumber=' + str(spec['version']))
    if spec.get('download_url') != expected or not re.fullmatch('[a-f0-9]{64}', spec.get('archive_sha256', '')):
        raise ValueError('Archive URL/version/checksum is not pinned')
    if not spec.get('files') or len({f['path'] for f in spec['files']}) != len(spec['files']):
        raise ValueError('An exact file manifest is required')
    for item in spec['files']:
        safe_member(item['path'])
        if not re.fullmatch('[a-f0-9]{64}', item.get('sha256', '')):
            raise ValueError('Every file requires a SHA-256 checksum')


def safe_member(name: str) -> PurePosixPath:
    path = PurePosixPath(name)
    if (not name or '\\' in name or ':' in name or path.is_absolute()
            or any(part in {'', '..', '.'} or part.rstrip(' .') != part
                   or part.split('.')[0].casefold() in {'con', 'prn', 'aux', 'nul',
                       *(f'com{i}' for i in range(1, 10)), *(f'lpt{i}' for i in range(1, 10))}
                   for part in name.split('/'))):
        raise ValueError('Unsafe archive member')
    return path


def verified_members(content: bytes, spec: dict) -> dict[str, bytes]:
    validate_spec(spec)
    if len(content) > MAX_ARCHIVE or sha256(content) != spec['archive_sha256']:
        raise ValueError('Archive checksum/size mismatch; existing artifacts remain untouched')
    expected = {f['path']: f for f in spec['files']}
    members = {}
    with zipfile.ZipFile(io.BytesIO(content)) as archive:
        entries = archive.infolist()
        if len(entries) > 1000 or sum(x.file_size for x in entries) > MAX_EXPANDED:
            raise ValueError('Expanded archive exceeds audit limits')
        for item in entries:
            safe_member(item.filename.rstrip('/'))
            if item.is_dir():
                continue
            if (item.filename not in expected or item.filename in members or item.flag_bits & 1
                    or stat.S_ISLNK(item.external_attr >> 16)):
                raise ValueError('Unexpected, repeated, encrypted or linked archive member')
            data = archive.read(item)
            info = expected[item.filename]
            if len(data) != info['bytes'] or sha256(data) != info['sha256']:
                raise ValueError('Extracted file checksum/size mismatch')
            members[item.filename] = data
    if set(members) != set(expected):
        raise ValueError('Archive does not contain the exact reviewed files')
    return members


class PublicArchiveRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        from urllib.parse import urlsplit
        url = urlsplit(newurl)
        if (url.scheme != 'https' or url.hostname not in {'www.kaggle.com', 'storage.googleapis.com'}
                or url.username or url.password or url.port not in {None, 443}):
            raise ValueError('Unexpected download redirect; stop for review')
        return super().redirect_request(req, fp, code, msg, headers, newurl)


def acquire(spec: dict, root: Path, download: bool = False) -> dict:
    validate_spec(spec)
    # Keep every archive isolated from the canonical/model paths. Existing bytes
    # are verified rather than overwritten. Source names cannot introduce paths.
    folder = (root / spec['source'].replace('/', '__')).resolve()
    if not folder.is_relative_to(root.resolve()):
        raise ValueError('Audit destination escapes its storage root')
    archive = folder / 'original.zip'
    if archive.exists():
        if archive.stat().st_size > MAX_ARCHIVE:
            raise ValueError('Cached archive exceeds audit size limit')
        content = archive.read_bytes()
    elif download:
        request = urllib.request.Request(spec['download_url'], headers={'User-Agent': 'SkyLens-source-audit/1.0'})
        opener = urllib.request.build_opener(PublicArchiveRedirect())
        # One download attempt. Denials/limits are terminal; no retries/bypasses.
        with opener.open(request, timeout=30) as response:
            content = response.read(MAX_ARCHIVE + 1)
    else:
        raise FileNotFoundError('Pinned archive is absent; use --download for a public audit acquisition')
    members = verified_members(content, spec)
    # Validate all existing destinations before any new write.
    for name, payload in members.items():
        target = (folder / name).resolve()
        if not target.is_relative_to(folder):
            raise ValueError('Extracted destination escapes audit storage')
        if target.exists() and target.read_bytes() != payload:
            raise ValueError('Existing audit file differs; preserve and investigate')
    folder.mkdir(parents=True, exist_ok=True)
    if not archive.exists():
        with archive.open('xb') as file:
            file.write(content)
    for name, payload in members.items():
        target = folder / name
        if not target.exists():
            target.parent.mkdir(parents=True, exist_ok=True)
            with target.open('xb') as file:
                file.write(payload)
    return {'source': spec['source'], 'archive_sha256': sha256(content), 'files_verified': len(members),
            'role': 'audit_only_not_training', 'training_automatically_enabled': False}


def main():
    root = Path(__file__).resolve().parents[2]
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--manifest', type=Path, default=root/'config/phase5_sources.json')
    parser.add_argument('--download', action='store_true', help='Opt in to pinned public archive downloads')
    args = parser.parse_args()
    specs = json.loads(args.manifest.read_text(encoding='utf-8'))['sources']
    results = [acquire(spec, root/'data/raw/phase5', args.download) for spec in specs]
    print(json.dumps(results, indent=2))


if __name__ == '__main__':
    main()
