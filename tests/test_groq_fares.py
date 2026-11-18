import asyncio
import json
import ssl
from contextlib import asynccontextmanager
from datetime import datetime, timedelta, timezone
from pathlib import Path
from types import SimpleNamespace

import httpx
import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from backend.app.fare_service import FareService
from backend.app.flight_fares import IST, FlightSearch
from backend.app.flight_search import load_airports, router
from backend.app.groq_fare_estimator import DEFAULT_MODEL, DISCLAIMER, EstimateError, GroqFareEstimator, GroqSettings
from scripts.repository_guard import inspect


FIXTURE_KEY = 'gsk_' + 'x' * 52
RANGE = json.dumps({'estimated_low': 12500, 'estimated_high': 16000, 'currency': 'INR'})


@pytest.fixture
def query():
    depart = datetime.now(IST).date() + timedelta(days=10)
    return {'origin': 'PNQ', 'destination': 'DEL', 'journey': 'round_trip', 'departure_date': depart.isoformat(),
            'return_date': (depart + timedelta(days=2)).isoformat(), 'cabin': 'business',
            'travellers': {'adults': 1, 'children': 1, 'infants': 0}}


def completion(content=RANGE, finish='stop'):
    return httpx.Response(200, json={'id': 'software-fixture', 'object': 'chat.completion', 'created': 0,
                                     'model': DEFAULT_MODEL, 'choices': [{'index': 0, 'finish_reason': finish,
                                         'message': {'role': 'assistant', 'content': content}}]})


def test_config_uses_local_env_or_process_without_leaking_key(tmp_path, monkeypatch):
    for name in ('GROQ_API_KEY', 'GROQ_MODEL', 'GROQ_FREE_PLAN_CONFIRMED'):
        monkeypatch.delenv(name, raising=False)
    assert GroqSettings.load(tmp_path) == GroqSettings(DEFAULT_MODEL, '', False)
    (tmp_path / '.env').write_text(
        f'GROQ_API_KEY={FIXTURE_KEY}\nGROQ_FREE_PLAN_CONFIRMED=true\nGROQ_MODEL=openai/gpt-oss-120b\n', encoding='utf-8')
    monkeypatch.chdir(tmp_path.parent)
    local = GroqSettings.load(tmp_path)
    assert local == GroqSettings('openai/gpt-oss-120b', FIXTURE_KEY, True)
    assert FIXTURE_KEY not in repr(local)
    monkeypatch.setenv('GROQ_API_KEY', 'environment-key')
    assert GroqSettings.load(tmp_path) == GroqSettings('openai/gpt-oss-120b', 'environment-key', False)
    monkeypatch.setenv('GROQ_MODEL', DEFAULT_MODEL)
    monkeypatch.setenv('GROQ_FREE_PLAN_CONFIRMED', 'true')
    assert GroqSettings.load(tmp_path) == GroqSettings(DEFAULT_MODEL, 'environment-key', True)
    assert inspect('example.ts', FIXTURE_KEY.encode()) == ['provider token']


def test_configured_key_alone_cannot_enable_ungrounded_customer_fares(monkeypatch, tmp_path, query):
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
    monkeypatch.delenv('SKYLENS_EXPERIMENTAL_GROQ', raising=False)
    monkeypatch.setenv('SKYLENS_KIWI_FARES_ENABLED', 'false')
    with TestClient(main.app) as client:
        assert client.get('/flights/capabilities').json()['indicative_estimates'] is None
        response = client.post('/flights/estimate', json=query)
        assert response.status_code == 503
        assert response.json()['detail']['code'] == 'no_fare_evidence'
        assert 'estimated_low' not in response.json()


@pytest.mark.parametrize('explicit_ca', [False, True])
def test_windows_groq_transport_uses_system_trust_unless_ca_is_configured(monkeypatch, explicit_ca):
    from backend.app import groq_fare_estimator as provider

    captured = {}
    def capture_client(**kwargs):
        captured.update(kwargs)
        return httpx.AsyncClient(transport=httpx.MockTransport(lambda _: completion()))

    monkeypatch.setattr(provider, 'sys', SimpleNamespace(platform='win32'), raising=False)
    monkeypatch.setattr(provider, 'AsyncClient', capture_client)
    monkeypatch.delenv('SSL_CERT_FILE', raising=False)
    monkeypatch.delenv('SSL_CERT_DIR', raising=False)
    if explicit_ca:
        monkeypatch.setenv('SSL_CERT_FILE', 'explicit-ca.pem')
    estimator = GroqFareEstimator(GroqSettings(DEFAULT_MODEL, FIXTURE_KEY, True))
    try:
        verify = captured.get('verify')
        if explicit_ca:
            assert verify is True
        else:
            assert isinstance(verify, ssl.SSLContext)
            assert verify.verify_mode == ssl.CERT_REQUIRED
            assert verify.check_hostname is True
    finally:
        asyncio.run(estimator.close())


@pytest.fixture
def app_client():
    @asynccontextmanager
    async def lifespan(app):
        yield
        await app.state.groq_estimator.close()

    def make(respond, *, key=FIXTURE_KEY, confirmed=True, timeout=3, cache_path=None):
        calls = []

        async def transport(request):
            calls.append(request)
            return await respond(request) if asyncio.iscoroutinefunction(respond) else respond(request)

        cache = {'cache_path': cache_path} if cache_path is not None else {}
        estimator = GroqFareEstimator(GroqSettings(DEFAULT_MODEL, key, confirmed),
                                      httpx.AsyncClient(transport=httpx.MockTransport(transport)), timeout=timeout, **cache)
        app = FastAPI(lifespan=lifespan)
        app.include_router(router)
        app.state.flight_airports = load_airports(Path(__file__).resolve().parents[1])
        app.state.fare_service = FareService()
        app.state.groq_estimator = estimator
        return TestClient(app), calls

    return make


def test_structured_round_trip_and_prompt_scope(app_client, query):
    client, calls = app_client(lambda _: completion())
    with client:
        capabilities = client.get('/flights/capabilities').json()
        assert capabilities['indicative_estimates']['children'] is True
        assert capabilities['live_quotes'] is capabilities['ml_estimates'] is None
        response = client.post('/flights/experimental/groq-estimate', json=query)
        assert response.status_code == 200
        assert response.headers['cache-control'] == 'no-store'
        payload = response.json()
        assert datetime.fromisoformat(payload.pop('estimated_at')).tzinfo is not None
        assert payload == {
            'estimated_low': 12500, 'estimated_high': 16000, 'currency': 'INR', 'journey_type': 'round_trip',
            'origin': 'PNQ', 'destination': 'DEL', 'departure_date': query['departure_date'], 'return_date': query['return_date'],
            'cabin_class': 'business', 'passenger_count': 2, 'estimation_source': 'groq_indicative', 'disclaimer': DISCLAIMER,
            'airline': None, 'airline_name': None,
        }
        assert client.post('/flights/search', json=query).status_code == 503
    request, = calls
    assert str(request.url) == 'https://api.groq.com/openai/v1/chat/completions'
    assert request.headers.get('authorization') == f'Bearer {FIXTURE_KEY}'
    body = json.loads(request.content)
    assert body['model'] == DEFAULT_MODEL
    assert body['max_completion_tokens'] == 384
    assert body['temperature'] == 0
    assert body['service_tier'] == 'on_demand' and 'tools' not in body
    assert body['response_format']['json_schema']['strict'] is True
    context = json.loads(body['messages'][-1]['content'])
    assert 1000 < context.pop('straight_line_distance_km_each_way') < 1400
    assert context.pop('days_until_departure') == 10
    assert context == query
    assert FIXTURE_KEY not in response.text and FIXTURE_KEY.encode() not in request.content


def test_unconfigured_and_unsupported_inputs_never_contact_groq(app_client, query, caplog):
    for key, confirmed, reason in [('', True, 'missing_key'), (FIXTURE_KEY, False, 'free_plan_unconfirmed')]:
        with caplog.at_level('INFO'):
            client, calls = app_client(lambda _: completion(), key=key, confirmed=confirmed)
        with client:
            assert client.get('/flights/capabilities').json()['indicative_estimates'] is None
            error = client.post('/flights/experimental/groq-estimate', json=query)
            assert error.status_code == 503
            assert error.json()['detail'] == {'code': 'unconfigured', 'retryable': True,
                'message': 'Fare estimate temporarily unavailable. Please try again.'}
        assert reason in caplog.text and FIXTURE_KEY not in caplog.text
        assert calls == []

    client, calls = app_client(lambda _: completion())
    with client:
        for change in [{'cabin': 'first'}, {'origin': 'LHR'}, {'destination': query['origin']},
                       {'journey': 'multi_city'}, {'return_date': '2000-01-01'}, {'travellers': {'adults': 0}},
                       {'travellers': {'adults': 1, 'infants': 1}}, {'airline': 'not-a-field'}]:
            assert client.post('/flights/experimental/groq-estimate', json=query | change).status_code == 422
        assert calls == []
        response = client.post('/flights/experimental/groq-estimate', json=query | {'journey': 'one_way', 'return_date': None})
        assert response.status_code == 200 and response.json()['return_date'] is None
    assert len(calls) == 1


@pytest.mark.parametrize('content', [
    '<not JSON>', '{}', None, '{"estimated_low":8000,"currency":"INR"}',
    '{"estimated_low":-8000,"estimated_high":12000,"currency":"INR"}',
    '{"estimated_low":13000,"estimated_high":12000,"currency":"INR"}',
    '{"estimated_low":10000,"estimated_high":10000,"currency":"INR"}',
    '{"estimated_low":true,"estimated_high":12000,"currency":"INR"}',
    '{"estimated_low":null,"estimated_high":12000,"currency":"INR"}',
    '{"estimated_low":9000,"estimated_high":12000,"currency":"USD"}',
])
def test_bad_ranges_fail_closed_without_retries(app_client, query, content):
    client, calls = app_client(lambda _: completion(content))
    with client:
        response = client.post('/flights/experimental/groq-estimate', json=query)
        assert response.status_code == 502
        assert response.json()['detail']['code'] == 'invalid_response'
        assert response.json()['detail']['retryable'] is True
    assert 'estimated_low' not in response.json() and len(calls) == 1


def test_abstention_and_truncation(app_client, query):
    client, _ = app_client(lambda _: completion('{"estimated_low":null,"estimated_high":null,"currency":"INR"}'))
    with client:
        assert client.post('/flights/experimental/groq-estimate', json=query).json()['detail']['code'] == 'no_estimate'
    client, _ = app_client(lambda _: completion(finish='length'))
    with client:
        assert client.post('/flights/experimental/groq-estimate', json=query).json()['detail']['code'] == 'invalid_response'


def test_broad_fallback_range_is_withheld_instead_of_rescaled(app_client, query):
    client, calls = app_client(lambda _: completion('{"estimated_low":2000,"estimated_high":4000,"currency":"INR"}'))
    with client:
        response = client.post('/flights/experimental/groq-estimate', json=query)
    assert response.status_code == 422
    assert response.json()['detail']['code'] == 'no_estimate'
    assert 'estimated_low' not in response.json() and len(calls) == 1


def test_identical_trip_reuses_saved_range_after_restart(app_client, query, tmp_path):
    database = tmp_path / 'estimates.sqlite3'
    first, calls = app_client(lambda _: completion(), cache_path=database)
    with first:
        original = first.post('/flights/experimental/groq-estimate', json=query)
        assert original.status_code == 200
        assert first.post('/flights/experimental/groq-estimate', json=query).json() == original.json()
    assert len(calls) == 1

    next_start, calls = app_client(lambda _: completion('{"estimated_low":3200,"estimated_high":4000,"currency":"INR"}'),
                                   cache_path=database)
    with next_start:
        same = next_start.post('/flights/experimental/groq-estimate', json=query | {'airline': None})
        assert same.json() == original.json()
        assert calls == []
        selected = next_start.post('/flights/experimental/groq-estimate', json=query | {'airline': 'indigo'})
        assert selected.status_code == 200
        assert selected.json()['airline_name'] == 'IndiGo'
        assert selected.json()['estimated_low'] == 3200
        assert next_start.post('/flights/experimental/groq-estimate', json=query | {'airline': 'indigo'}).json() == selected.json()
    assert len(calls) == 1
    context = json.loads(json.loads(calls[0].content)['messages'][-1]['content'])
    assert context['airline_preference'] == 'IndiGo'


def test_airline_catalogue_and_invalid_airline(app_client, query):
    client, calls = app_client(lambda _: completion())
    with client:
        options = client.get('/flights/capabilities').json()
        assert {item['name'] for item in options['airlines']} == {
            'Air India', 'Air India Express', 'Akasa Air', 'Alliance Air', 'FLY91', 'IndiaOne Air', 'IndiGo', 'SpiceJet', 'Star Air',
        }
        assert 'air_india' in options['indicative_estimates']['airlines']
        assert client.post('/flights/experimental/groq-estimate', json=query | {'airline': 'unknown'}).status_code == 422
    assert calls == []


def test_expired_estimate_gets_a_new_timestamp(app_client, query, tmp_path, monkeypatch):
    saved_at = int(datetime.now(timezone.utc).timestamp())
    monkeypatch.setattr('backend.app.groq_fare_estimator.time', lambda: saved_at)
    client, calls = app_client(lambda _: completion(), cache_path=tmp_path / 'estimates.sqlite3')
    with client:
        original = client.post('/flights/experimental/groq-estimate', json=query).json()
        saved_at += 24 * 60 * 60 - 1
        assert client.post('/flights/experimental/groq-estimate', json=query).json() == original
        saved_at += 1
        refreshed = client.post('/flights/experimental/groq-estimate', json=query).json()
        assert refreshed['estimated_at'] != original['estimated_at']
    assert len(calls) == 2


def test_customer_estimate_only_uses_a_covered_supervised_model(app_client, query):
    from backend.app.flight_fares import SearchSupport

    class ValidatedModel:
        support = SearchSupport(journeys=['round_trip'], cabins=['business'], children=True)

        def supports_route(self, search):
            return (search.origin, search.destination) == ('PNQ', 'DEL')

        async def search(self, search):
            return [{'source': 'ml_estimate', 'id': 'validated-fixture', 'source_name': 'Contract fixture',
                     'journey': search.journey, 'cabin': search.cabin, 'travellers': search.travellers,
                     'retrieved_at': datetime.now(timezone.utc),
                     'fare': {'amount': '14500', 'currency': 'INR', 'basis': 'party_total',
                              'taxes': 'included', 'fees': 'included'}}]

    client, calls = app_client(lambda _: completion())
    client.app.state.fare_service = FareService(model=ValidatedModel())
    with client:
        model = client.post('/flights/estimate', json=query)
        assert model.status_code == 200
        assert model.json()['results'][0]['source'] == 'ml_estimate'
        assert calls == []
        unsupported = client.post('/flights/estimate', json=query | {'origin': 'BOM'})
        assert unsupported.status_code == 503
        assert unsupported.json()['detail']['code'] == 'no_fare_evidence'
        assert 'estimated_low' not in unsupported.json()
    assert calls == []


@pytest.mark.parametrize(('status', 'headers', 'app_status', 'code'), [
    (401, {}, 503, 'authentication'), (403, {}, 503, 'model_unavailable'), (404, {}, 503, 'model_unavailable'),
    (429, {'retry-after': '19'}, 429, 'rate_limit'),
    (429, {'retry-after': '100', 'x-ratelimit-remaining-requests': '0'}, 429, 'quota'),
    (402, {}, 429, 'quota'), (500, {}, 502, 'unavailable'),
])
def test_provider_errors_and_throttling_do_not_reveal_diagnostics(app_client, query, caplog, status, headers, app_status, code):
    client, calls = app_client(lambda _: httpx.Response(status, headers=headers,
                                                       json={'error': {'message': f'private provider detail {FIXTURE_KEY}'}}))
    with client, caplog.at_level('DEBUG'):
        response = client.post('/flights/experimental/groq-estimate', json=query)
        assert response.status_code == app_status
        assert response.json()['detail']['code'] == code
        assert response.json()['detail']['message'] == 'Fare estimate temporarily unavailable. Please try again.'
        assert f'provider_status={status} category={code}' in caplog.text
        assert FIXTURE_KEY not in response.text + caplog.text
        assert 'private provider detail' not in response.text + caplog.text
        if app_status == 429:
            again = client.post('/flights/experimental/groq-estimate', json=query)
            assert again.status_code == 429 and int(again.headers['Retry-After']) > 0
    assert len(calls) == 1


def test_timeout_and_backend_connection_failure(app_client, query):
    async def slow(request):
        await asyncio.sleep(1)
        return completion()

    def connection_failure(request):
        raise httpx.ConnectError('diagnostic data', request=request)

    for handler, status in [(slow, 504), (connection_failure, 502)]:
        client, calls = app_client(handler, timeout=0.05 if status == 504 else 3)
        with client:
            response = client.post('/flights/experimental/groq-estimate', json=query)
            assert response.status_code == status
            assert response.json()['detail']['retryable'] is True
        assert len(calls) == 1


def test_an_in_flight_estimate_does_not_resend(query):
    async def scenario():
        start, finish = asyncio.Event(), asyncio.Event()
        calls = 0

        async def respond(request):
            nonlocal calls
            calls += 1
            start.set()
            await finish.wait()
            return completion()

        client = httpx.AsyncClient(transport=httpx.MockTransport(respond))
        estimator = GroqFareEstimator(GroqSettings(DEFAULT_MODEL, FIXTURE_KEY, True), client)
        payload = FlightSearch.model_validate(query)
        first = asyncio.create_task(estimator.estimate(payload, None))
        try:
            await start.wait()
            with pytest.raises(EstimateError) as duplicate:
                await estimator.estimate(FlightSearch.model_validate(query | {'origin': 'BOM'}), None)
            assert duplicate.value.code == 'busy'
            same = asyncio.create_task(estimator.estimate(payload, None))
            await asyncio.sleep(0)
        finally:
            finish.set()
        try:
            assert await first == await same
            assert calls == 1
        finally:
            await estimator.close()

    asyncio.run(scenario())
