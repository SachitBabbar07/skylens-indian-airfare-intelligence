"""Portable archive-intake and read-only acquisition contracts; fixtures only."""
import csv
import io
import json
import zipfile
from copy import deepcopy
from pathlib import Path
from urllib.request import Request

import pytest
from fastapi import FastAPI, HTTPException
from fastapi.testclient import TestClient

from backend.app.acquisition import review_status, router
from skylens.quotes import Quote
from skylens.source_audit import acquire, sha256, verified_members, PublicArchiveRedirect


def archive_fixture(name='observations.csv'):
    payload = b'fixture_column\nsoftware_fixture_only\n'
    buffer = io.BytesIO()
    with zipfile.ZipFile(buffer, 'w') as archive:
        archive.writestr(name, payload)
    content = buffer.getvalue()
    spec = dict(source='software_fixture/dataset', version=1, declared_license='CC0: Public Domain',
                role='audit_only_not_training', training_eligible=False,
                download_url='https://www.kaggle.com/api/v1/datasets/download/software_fixture/dataset?datasetVersionNumber=1',
                archive_sha256=sha256(content), files=[dict(path=name, bytes=len(payload), sha256=sha256(payload))])
    return content, spec


def test_pinned_archive_verifies_without_network_or_training(tmp_path, monkeypatch):
    content, spec = archive_fixture()
    folder = tmp_path/'software_fixture__dataset'
    folder.mkdir()
    (folder/'original.zip').write_bytes(content)
    def forbidden(*args, **kwargs):
        pytest.fail('Verification must not call the network')
    monkeypatch.setattr('urllib.request.build_opener', forbidden)
    result = acquire(spec, tmp_path)
    assert result['files_verified'] == 1 and result['training_automatically_enabled'] is False
    assert acquire(spec, tmp_path) == result  # byte-identical replay
    assert not list(tmp_path.rglob('*.cbm'))


def test_default_does_not_download_or_create_missing_archive(tmp_path, monkeypatch):
    _, spec = archive_fixture()
    monkeypatch.setattr('urllib.request.build_opener', lambda *a: pytest.fail('Opt-in required'))
    with pytest.raises(FileNotFoundError):
        acquire(spec, tmp_path)
    assert not list(tmp_path.iterdir())


@pytest.mark.parametrize('member', ['../escape.csv', '/absolute.csv', 'C:/drive.csv',
                                  'folder\\escape.csv', 'a/../escape.csv', 'a//alias.csv', 'CON.csv'])
def test_untrusted_archive_names_cannot_escape_or_alias_windows_paths(member):
    content, spec = archive_fixture(member)
    with pytest.raises(ValueError):
        verified_members(content, spec)


@pytest.mark.parametrize('changes', [dict(training_eligible=True), dict(role='training'),
                                    dict(declared_license='Unknown'), dict(version=True),
                                    dict(download_url='https://unreviewed.invalid/file.zip')])
def test_labels_or_other_urls_cannot_promote_audit_sources(changes):
    content, spec = archive_fixture()
    with pytest.raises(ValueError):
        verified_members(content, {**spec, **changes})


def test_bad_archive_and_file_hashes_fail_before_any_file_is_written(tmp_path):
    content, spec = archive_fixture()
    with pytest.raises(ValueError):
        verified_members(content+b'changed', spec)
    broken = deepcopy(spec)
    broken['files'][0]['sha256'] = '0'*64
    with pytest.raises(ValueError):
        verified_members(content, broken)
    folder = tmp_path/'software_fixture__dataset'
    folder.mkdir()
    (folder/'original.zip').write_bytes(content)
    (folder/'observations.csv').write_bytes(b'existing bytes must survive')
    with pytest.raises(ValueError):
        acquire(spec, tmp_path)
    assert (folder/'observations.csv').read_bytes() == b'existing bytes must survive'


def test_expansion_limit_is_checked_before_extracting(monkeypatch):
    content, spec = archive_fixture()
    monkeypatch.setattr('skylens.source_audit.MAX_EXPANDED', 1)
    with pytest.raises(ValueError):
        verified_members(content, spec)


@pytest.mark.parametrize('url', ['http://storage.googleapis.com/file', 'https://unreviewed.invalid/file',
                               'https://user@storage.googleapis.com/file', 'https://storage.googleapis.com:444/file'])
def test_download_redirects_cannot_downgrade_or_escape_approved_hosts(url):
    with pytest.raises(ValueError):
        PublicArchiveRedirect().redirect_request(Request('https://www.kaggle.com/'), None, 302, 'Found', {}, url)


def test_manual_template_has_headers_only_and_unknown_money_semantics():
    app = FastAPI()
    app.include_router(router)
    client = TestClient(app)
    response = client.get('/acquisition/template.csv')
    assert response.status_code == 200 and 'attachment' in response.headers['content-disposition']
    reader = csv.DictReader(io.StringIO(response.text))
    assert list(reader) == [] and reader.fieldnames == list(Quote.model_fields)
    assert {'license_name', 'license_url', 'reuse_status', 'booking_lead_days'} <= set(reader.fieldnames)
    schema = client.get('/acquisition/schema').json()
    assert schema['training_automatically_enabled'] is False
    fields = schema['quote']['properties']
    assert fields['currency']['default'] is None
    assert fields['reuse_status']['default'] == 'unknown'
    assert fields['booking_lead_days']['default'] is None


def test_missing_or_unsafe_review_cannot_enable_prediction(tmp_path):
    with pytest.raises(HTTPException) as error:
        review_status(tmp_path)
    assert error.value.status_code == 503
    path = tmp_path/'data/metadata/phase5/acquisition_decision.json'
    path.parent.mkdir(parents=True)
    path.write_text(json.dumps(dict(customer_fare_prediction_available=True, training_automatically_enabled=True)))
    with pytest.raises(HTTPException):
        review_status(tmp_path)
