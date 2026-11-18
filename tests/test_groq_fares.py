"""The retired Groq price path cannot provide, replace or delay a numerical estimate."""

import asyncio
from datetime import datetime, timedelta
from pathlib import Path
from types import SimpleNamespace

import httpx
import pytest
from fastapi.testclient import TestClient

from backend.app.flight_fares import IST
from scripts.repository_guard import inspect


FIXTURE_KEY = 'gsk_' + 'x' * 52


@pytest.mark.parametrize('groq_failure', ['timeout', 'connection', 'quota', 'invented_range'])
def test_groq_is_never_called_for_a_customer_fare(monkeypatch, tmp_path, groq_failure, caplog):
    pytest.importorskip('catboost')
    from backend.app import main

    project = Path(__file__).resolve().parents[1]
    (tmp_path / 'reports').mkdir()
    (tmp_path / 'reports/airport_fare_coverage.csv').write_bytes(
        (project / 'reports/airport_fare_coverage.csv').read_bytes())
    monkeypatch.setattr(main, 'ROOT', tmp_path)
    monkeypatch.setattr(main, 'ModelStore', lambda: SimpleNamespace(models={}, errors={}))
    monkeypatch.setattr(main, 'historical_evidence', lambda _: None)
    monkeypatch.setenv('GROQ_API_KEY', FIXTURE_KEY)
    monkeypatch.setenv('GROQ_FREE_PLAN_CONFIRMED', 'true')
    monkeypatch.setenv('SKYLENS_EXPERIMENTAL_GROQ', 'true')
    monkeypatch.setenv('SKYLENS_KIWI_FARES_ENABLED', 'false')
    calls = []
    async def transport(self, request, **kwargs):
        calls.append(request.url.host)
        if groq_failure == 'timeout':
            raise httpx.ReadTimeout('mocked Groq timeout')
        if groq_failure == 'connection':
            raise httpx.ConnectError('mocked Groq outage')
        if groq_failure == 'quota':
            return httpx.Response(429)
        return httpx.Response(200, json={'estimated_low': 1, 'estimated_high': 2, 'currency': 'INR'})

    monkeypatch.setattr(httpx.AsyncClient, 'send', transport)
    query = {'origin': 'DEL', 'destination': 'IXC', 'journey': 'one_way',
             'departure_date': (datetime.now(IST).date() + timedelta(days=7)).isoformat()}
    with TestClient(main.app) as client:
        response = client.post('/flights/estimate', json=query)
        assert response.status_code == 503
        assert response.json()['detail']['code'] == 'unconfigured'
        assert 'estimated_low' not in response.json() and calls == []
        assert client.get('/flights/capabilities').json()['indicative_estimates'] is None
        assert '/flights/experimental/groq-estimate' not in client.get('/openapi.json').json()['paths']
        assert client.post('/flights/experimental/groq-estimate', json=query).status_code in (404, 405)
        assert FIXTURE_KEY not in response.text + caplog.text and calls == []


def test_groq_tokens_remain_covered_by_repository_scan():
    assert inspect('example.ts', FIXTURE_KEY.encode()) == ['provider token']
