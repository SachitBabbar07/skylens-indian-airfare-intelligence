"""Native acceptance checks for the Phase 6 read-only research surface."""
import math

import pytest
from fastapi.testclient import TestClient

from backend.app.main import app

pytestmark = pytest.mark.local_data


@pytest.fixture(scope='module')
def client():
    with TestClient(app) as value:
        yield value


def test_historical_route_catalog_matches_frozen_counts_and_never_returns_prices(client):
    response = client.get('/research/evidence')
    assert response.status_code == 200 and response.headers.get('content-encoding') == 'gzip'
    data = response.json()
    assert data['currency'] is None and data['research_only'] is True
    routes = data['routes']
    assert len({(r['origin'], r['destination']) for r in routes}) == data['distinct_directional_routes'] == 720
    for cohort in data['cohorts']:
        records = [r for r in routes if r['cohort_id'] == cohort['id']]
        assert sum(r['observations'] for r in records) == cohort['retained_observations']
        assert len({(r['origin'], r['destination']) for r in records}) == cohort['directional_routes']
        assert all(set(r) == {'origin','destination','cabin_class','cohort_id','observations'} for r in records)
    assert any(c['role'] == 'external_challenge' for c in data['cohorts'])


def test_missing_model_keeps_historical_coverage_and_blocks_research_profiles(client, monkeypatch):
    monkeypatch.setattr(app.state.store, 'models', {})
    assert client.get('/health').status_code == 503
    assert client.get('/supported-options').status_code == 503
    assert client.get('/research/evidence').json()['distinct_directional_routes'] == 720
    directory = client.get('/airports', params={'supported_only': False, 'query':'PNQ'}).json()
    assert directory['total'] == 1 and directory['airports'][0]['serving_status'] == 'model_unavailable'
    assert not directory['airports'][0]['research_eligible']


@pytest.mark.parametrize('value', [math.nan, math.inf, -math.inf])
def test_nonfinite_research_input_is_safely_rejected(client, value):
    # Deliberately send invalid numeric source input without the client's JSON validation.
    import json
    body = json.dumps(dict(model_id='cabin_2023', origin='DEL', destination='BOM', airline='Air India',
                           cabin_class='Economy', stops=0, days_left=1, duration_minutes=value,
                           departure_hour=8, research_acknowledged=True))
    response = client.post('/research/predict', content=body, headers={'Content-Type':'application/json'})
    assert response.status_code == 422
    assert any('duration_minutes' in item['loc'] for item in response.json()['detail'])
    assert '"input"' not in response.text
