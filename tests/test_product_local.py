"""Real frozen artifacts: product correction must leave science unchanged."""
import hashlib
import json
from pathlib import Path

import pytest
from fastapi.testclient import TestClient
from backend.app.main import app
from backend.app.schemas import PredictionRequest

pytestmark = pytest.mark.local_data
ROOT = Path(__file__).resolve().parents[1]


@pytest.fixture(scope='module')
def client():
    with TestClient(app) as value:
        yield value


def actual_scenario():
    return dict(model_id='cabin_2023', origin='AMD', destination='BLR', airline='Air India',
                cabin_class='Business', stops=1, days_left=1, duration_minutes=335.0,
                departure_hour=7+55/60, research_acknowledged=True)


def test_raw_prediction_and_native_shap_unchanged(client):
    body = actual_scenario()
    result = client.post('/research/predict', json=body)
    explanation = client.post('/research/explain', json=body)
    assert result.status_code == explanation.status_code == 200
    r, x = result.json(), explanation.json()
    bundle, frame, support = app.state.store.frame(PredictionRequest(**body))
    native = float(bundle['model'].predict(frame)[0])
    assert native == pytest.approx(54757.14, abs=.01)
    assert r['estimate'] == native == x['estimate']
    assert r['currency'] is x['currency'] is None
    assert r['historical_support'] == support == 407
    assert r['unit_verification'] == x['unit_verification'] == 'unverified'
    assert len(x['contributions']) == 13
    assert x['baseline'] + sum(c['contribution'] for c in x['contributions']) == pytest.approx(native, abs=1e-8)
    assert x['additive_error'] < 1e-8 and 'not rupee' in x['interpretation']
    assert r['interval'] is None


def test_metadata_label_alone_cannot_enable_customer_or_convert_raw_output(client, monkeypatch):
    meta = app.state.store.models['cabin_2023']['meta']
    monkeypatch.setitem(meta, 'currency', 'INR')
    monkeypatch.setitem(meta, 'unit', 'INR')
    r = client.post('/research/predict', json=actual_scenario()).json()
    assert r['currency'] is None and r['unit'] == 'source fare units'
    assert r['estimate'] == pytest.approx(54757.14, abs=.01)
    assert client.get('/capabilities').json()['fare_estimation']['available'] is False


def test_customer_requests_never_invoke_research_inference(client, monkeypatch):
    def forbidden(*args, **kwargs):
        pytest.fail('Customer request reached the research model')
    monkeypatch.setattr(app.state.store, 'predict', forbidden)
    monkeypatch.setattr(app.state.store, 'explain', forbidden)
    for path in ['/predict', '/explain', '/fare-estimate']:
        assert client.post(path, json=actual_scenario()).status_code == 503


def test_all_frozen_data_models_and_scientific_metadata_preserved():
    baseline = json.loads((ROOT/'data/metadata/product_correction/preservation_baseline.json').read_text())
    assert len(baseline['frozen_files']) == 56
    for name, expected in baseline['frozen_files'].items():
        path = ROOT/name
        assert path.stat().st_size == expected['bytes'], name
        assert hashlib.sha256(path.read_bytes()).hexdigest() == expected['sha256'], name
