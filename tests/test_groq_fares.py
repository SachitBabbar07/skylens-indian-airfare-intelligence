import asyncio
import json
from contextlib import asynccontextmanager
from datetime import datetime, timedelta
from pathlib import Path

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
RANGE = json.dumps({'estimated_low': 9000, 'estimated_high': 16000, 'currency': 'INR'})


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


@pytest.fixture
def app_client():
    @asynccontextmanager
    async def lifespan(app):
        yield
        await app.state.groq_estimator.close()

    def make(respond, *, key=FIXTURE_KEY, confirmed=True, timeout=3):
        calls = []

        async def transport(request):
            calls.append(request)
            return await respond(request) if asyncio.iscoroutinefunction(respond) else respond(request)

        estimator = GroqFareEstimator(GroqSettings(DEFAULT_MODEL, key, confirmed),
                                      httpx.AsyncClient(transport=httpx.MockTransport(transport)), timeout=timeout)
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
        response = client.post('/flights/estimate', json=query)
        assert response.status_code == 200
        assert response.headers['cache-control'] == 'no-store'
        assert response.json() == {
            'estimated_low': 9000, 'estimated_high': 16000, 'currency': 'INR', 'journey_type': 'round_trip',
            'origin': 'PNQ', 'destination': 'DEL', 'departure_date': query['departure_date'], 'return_date': query['return_date'],
            'cabin_class': 'business', 'passenger_count': 2, 'estimation_source': 'groq_indicative', 'disclaimer': DISCLAIMER,
        }
        assert client.post('/flights/search', json=query).status_code == 503
    request, = calls
    assert str(request.url) == 'https://api.groq.com/openai/v1/chat/completions'
    assert request.headers.get('authorization') == f'Bearer {FIXTURE_KEY}'
    body = json.loads(request.content)
    assert body['model'] == DEFAULT_MODEL
    assert body['max_completion_tokens'] == 384
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
            error = client.post('/flights/estimate', json=query)
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
            assert client.post('/flights/estimate', json=query | change).status_code == 422
        assert calls == []
        response = client.post('/flights/estimate', json=query | {'journey': 'one_way', 'return_date': None})
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
        response = client.post('/flights/estimate', json=query)
        assert response.status_code == 502
        assert response.json()['detail']['code'] == 'invalid_response'
        assert response.json()['detail']['retryable'] is True
    assert 'estimated_low' not in response.json() and len(calls) == 1


def test_abstention_and_truncation(app_client, query):
    client, _ = app_client(lambda _: completion('{"estimated_low":null,"estimated_high":null,"currency":"INR"}'))
    with client:
        assert client.post('/flights/estimate', json=query).json()['detail']['code'] == 'no_estimate'
    client, _ = app_client(lambda _: completion(finish='length'))
    with client:
        assert client.post('/flights/estimate', json=query).json()['detail']['code'] == 'invalid_response'


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
        response = client.post('/flights/estimate', json=query)
        assert response.status_code == app_status
        assert response.json()['detail']['code'] == code
        assert response.json()['detail']['message'] == 'Fare estimate temporarily unavailable. Please try again.'
        assert f'provider_status={status} category={code}' in caplog.text
        assert FIXTURE_KEY not in response.text + caplog.text
        assert 'private provider detail' not in response.text + caplog.text
        if app_status == 429:
            again = client.post('/flights/estimate', json=query)
            assert again.status_code == 429 and int(again.headers['Retry-After']) > 0
    assert len(calls) == 1


def test_timeout_and_backend_connection_failure(app_client, query):
    async def slow(request):
        await asyncio.sleep(1)
        return completion()

    def connection_failure(request):
        raise httpx.ConnectError('diagnostic data', request=request)

    for handler, status in [(slow, 504), (connection_failure, 502)]:
        client, calls = app_client(handler, timeout=0.05)
        with client:
            response = client.post('/flights/estimate', json=query)
            assert response.status_code == status
            assert response.json()['detail']['retryable'] is True
        assert len(calls) == 1


def test_an_in_flight_estimate_does_not_resend(query):
    async def scenario():
        start, finish = asyncio.Event(), asyncio.Event()

        async def respond(request):
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
                await estimator.estimate(payload, None)
            assert duplicate.value.code == 'busy'
        finally:
            finish.set()
            await first
            await estimator.close()

    asyncio.run(scenario())
