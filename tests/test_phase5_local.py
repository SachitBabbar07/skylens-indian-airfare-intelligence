"""Native workspace integration and frozen scientific-state preservation."""
import hashlib
import json
from pathlib import Path

import pytest
from fastapi.testclient import TestClient
from backend.app.main import app

pytestmark = pytest.mark.local_data
ROOT = Path(__file__).resolve().parents[1]


def test_phase5_keeps_all_original_artifacts_and_training_pipeline_unchanged():
    baseline = json.loads((ROOT/'data/metadata/phase5/preservation_baseline.json').read_text())
    assert len(baseline['frozen_files']) == 56
    for name, info in baseline['frozen_files'].items():
        assert hashlib.sha256((ROOT/name).read_bytes()).hexdigest() == info['sha256'], name
    for name, expected in baseline['protected_pipeline_files'].items():
        assert hashlib.sha256((ROOT/name).read_bytes()).hexdigest() == expected, name


def test_native_application_exposes_empty_intake_without_enabling_customer_prices():
    with TestClient(app) as client:
        assert client.get('/health').status_code == 200
        response = client.get('/acquisition/status')
        assert response.status_code == 200
        review = response.json()
        assert review['verified_one_way_observations'] == review['verified_round_trip_observations'] == 0
        assert review['approved_sources'] == 0 and review['customer_fare_prediction_available'] is False
        assert client.post('/fare-estimate', json={}).status_code == 503
        assert client.post('/acquisition/status', json={'enable': True}).status_code == 405
        assert client.get('/acquisition/template.csv').text.count('\n') == 1
