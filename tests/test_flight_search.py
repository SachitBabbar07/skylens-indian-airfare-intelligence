import asyncio
from datetime import datetime, time, timedelta, timezone
from pathlib import Path

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from backend.app.fare_service import FareError, FareService
from backend.app.flight_fares import IST, SearchSupport
from backend.app.flight_search import load_airports, router


def test_estimate_uses_kiwi_for_exact_carrier_when_model_has_no_coverage(client, query):
    import asyncio
    import json

    import httpx

    from backend.app.kiwi_fares import KiwiFareProvider

    search = query | {'origin': 'DEL', 'destination': 'IXC', 'airline': 'indigo', 'cabin': 'economy',
                      'travellers': {'adults': 2, 'children': 0, 'infants': 0}}
    departure = search['departure_date']
    segment = {'from': 'DEL', 'to': 'IXC', 'fromCountry': 'India', 'toCountry': 'India', 'carrier': '6E',
               'cabinClass': 'Economy', 'flightNumber': '6E2147', 'departureTime': f'{departure}T11:20:00',
               'arrivalTime': f'{departure}T12:20:00'}
    outbound = {**segment, 'segments': [segment], 'stops': 0, 'durationSeconds': 3600}
    offer = {'id': 'software-fixture', 'price': 13200.0, 'tripType': 'oneway', 'outbound': outbound,
             'inbound': None, 'bookingUrl': 'https://booking.example.invalid/private'}
    seen = []

    def upstream(request):
        assert str(request.url) == 'https://mcp.kiwi.com'
        rpc = json.loads(request.content)
        seen.append(rpc['method'])
        if rpc['method'] == 'initialize':
            return httpx.Response(200, json={'jsonrpc': '2.0', 'id': rpc['id'],
                                           'result': {'protocolVersion': '2025-03-26'}})
        if rpc['method'] == 'notifications/initialized':
            return httpx.Response(202)
        args = rpc['params']['arguments']
        assert args['select_airlines'] == '6E' and args['cabinClass'] == 'M' and args['currency'] == 'INR'
        assert args['adults'] == 2 and args['departureDateFlexDays'] == 0
        assert args['departureDate'] == datetime.fromisoformat(departure).strftime('%d/%m/%Y')
        conflicting = {**offer, 'id': 'wrong-carrier', 'price': 4000,
                       'outbound': {**outbound, 'segments': [segment | {'carrier': 'AI'}]}}
        structured = {'currency': 'INR', 'passengers': search['travellers'], 'error': None,
                      'itineraries': [conflicting, offer]}
        result = {'jsonrpc': '2.0', 'id': rpc['id'], 'result': {'structuredContent': structured, 'isError': False}}
        return httpx.Response(200, headers={'Content-Type': 'text/event-stream'},
                              text=f'data: {json.dumps(result)}\n\n')

    provider = KiwiFareProvider(client=httpx.AsyncClient(transport=httpx.MockTransport(upstream)))
    client.app.state.fare_service = FareService(provider=provider, provider_cache_seconds=60)
    try:
        response = client.post('/flights/estimate', json=search)
        second = client.post('/flights/estimate', json=search)
    finally:
        asyncio.run(provider.close())
    assert response.status_code == 200
    assert second.json() == response.json()
    result = response.json()
    assert result['estimation_method'] == 'market_reference'
    assert result['price_scope'] == 'party_total' and result['passenger_count'] == 2
    assert result['taxes'] == result['fees'] == 'unknown'
    from decimal import Decimal
    assert Decimal(result['estimated_median']) == Decimal('13200')
    assert result['estimated_low'] == result['estimated_high']
    assert result['observation_count'] == 1
    assert 'booking.example' not in response.text and '6E2147' not in response.text
    assert 'results' not in result and 'legs' not in result
    assert seen == ['initialize', 'notifications/initialized', 'tools/call']


@pytest.fixture
def client():
    app = FastAPI()
    app.include_router(router)
    app.state.flight_airports = load_airports(Path(__file__).resolve().parents[1])
    app.state.fare_service = FareService()
    with TestClient(app) as test_client:
        yield test_client


@pytest.fixture
def query():
    day = datetime.now(IST).date() + timedelta(days=3)
    return {'origin': 'PNQ', 'destination': 'DEL', 'journey': 'one_way', 'departure_date': day.isoformat(),
            'cabin': 'economy', 'travellers': {'adults': 2, 'children': 0, 'infants': 0}}


def quote(request):
    def leg(origin, destination, day):
        departure = datetime.combine(day, time(10), tzinfo=IST)
        return {'origin': origin, 'destination': destination, 'departure': departure,
                'arrival': departure + timedelta(hours=2), 'airlines': ['Contract fixture'],
                'duration_minutes': 120, 'stops': 0}

    legs = [leg(request.origin, request.destination, request.departure_date)]
    if request.return_date:
        legs.append(leg(request.destination, request.origin, request.return_date))
    return {'id': 'test-only', 'source': 'live_quote', 'source_name': 'Contract fixture', 'availability': 'available',
            'retrieved_at': datetime.now(timezone.utc), 'journey': request.journey, 'cabin': request.cabin,
            'travellers': request.travellers, 'legs': legs,
            'fare': {'amount': '12000.50', 'currency': 'INR', 'basis': 'party_total', 'taxes': 'included', 'fees': 'unknown'}}


class Stub:
    def __init__(self, respond, *, route_supported=True, support=None):
        self.respond = respond
        self.requests = []
        self.route_supported = route_supported
        self.support = support or SearchSupport(journeys=['one_way', 'round_trip'], cabins=['economy', 'business'])

    def supports_route(self, request):
        return self.route_supported

    async def search(self, request):
        self.requests.append(request)
        return self.respond(request)


def test_directory_and_unconfigured_search(client, query):
    airports = {airport['code']: airport for airport in client.get('/flights/airports').json()['airports']}
    assert len(airports) == 165
    assert airports['PNQ']['city'] == 'Pune'
    assert airports['PNQ']['has_historical_evidence'] is True
    assert airports['AYJ']['has_historical_evidence'] is False
    capabilities = client.get('/flights/capabilities').json()
    assert capabilities['live_quotes'] is capabilities['ml_estimates'] is None
    response = client.post('/flights/search', json=query)
    assert response.status_code == 503
    assert response.json()['detail']['code'] == 'unconfigured'
    assert response.headers['Cache-Control'] == 'no-store'
    assert 'results' not in response.json()


@pytest.mark.parametrize('edits', [
    {'origin': 'LHR'}, {'destination': 'PNQ'}, {'destination': 'typo'}, {'departure_date': '2000-01-01'},
    {'journey': 'round_trip'}, {'journey': 'round_trip', 'return_date': '2000-01-01'},
    {'return_date': '2099-01-01'}, {'travellers': {'adults': 0}}, {'travellers': {'adults': '2'}},
    {'travellers': {'adults': 9, 'children': 1}}, {'travellers': {'adults': 1, 'infants': 2}}, {'cabin': 'executive'},
])
def test_validation_precedes_source_lookup(client, query, edits):
    provider = Stub(lambda request: [quote(request)])
    client.app.state.fare_service = FareService(provider=provider)
    assert client.post('/flights/search', json=query | edits).status_code == 422
    assert provider.requests == []


@pytest.mark.parametrize('round_trip', [False, True])
def test_preserves_available_quotes_and_currency(client, query, round_trip):
    def respond(request):
        first = quote(request)
        second = quote(request)
        second['id'] = 'second'
        second['fare'].update(currency='USD', amount='154.25')
        return [first, second]

    provider = Stub(respond)
    client.app.state.fare_service = FareService(provider=provider)
    if round_trip:
        query.update(journey='round_trip', return_date='2099-01-01', cabin='business')
    response = client.post('/flights/search', json=query)
    assert response.status_code == 200
    assert response.headers['Cache-Control'] == 'no-store'
    estimate = response.json()
    assert estimate['currency'] == 'INR' and estimate['price_scope'] == 'party_total'
    assert estimate['estimated_low'] == estimate['estimated_high'] == '12000.50'
    assert estimate['observation_count'] == 1
    assert estimate['taxes'] == 'included' and estimate['fees'] == 'unknown'
    assert estimate['passenger_count'] == 2 and estimate['cabin_class'] == query['cabin']
    assert estimate['journey_type'] == query['journey'] and estimate['return_date'] == query.get('return_date')
    assert '154.25' not in response.text


def test_empty_and_unsupported_are_distinct(client, query):
    provider = Stub(lambda request: [], support=SearchSupport(journeys=['one_way'], cabins=['economy'], max_travellers=2))
    client.app.state.fare_service = FareService(provider=provider)
    empty = client.post('/flights/search', json=query).json()
    assert empty['estimation_method'] == 'unavailable' and empty['estimated_low'] is None
    assert empty['source_status']['market'] == 'no_observations'
    for edits in [{'cabin': 'business'}, {'travellers': {'adults': 3}},
                  {'travellers': {'adults': 1, 'children': 1}}, {'travellers': {'adults': 1, 'infants': 1}}]:
        response = client.post('/flights/search', json=query | edits)
        assert response.status_code == 200
        assert response.json()['estimation_method'] == 'unavailable'
        assert response.json()['source_status']['market'] == 'unsupported'
    assert len(provider.requests) == 1


@pytest.mark.parametrize('defect', ['currency', 'basis', 'amount', 'airport', 'stale', 'missing_leg',
                                    'duplicate', 'shape', 'unknown_currency', 'wrong_party'])
def test_bad_response_fails_closed(client, query, defect):
    def respond(request):
        value = quote(request)
        if defect in {'currency', 'basis', 'amount'}:
            value['fare'].pop(defect)
        elif defect == 'airport':
            value['legs'][0]['origin'] = 'BOM'
        elif defect == 'stale':
            value['retrieved_at'] -= timedelta(minutes=5)
        elif defect == 'missing_leg':
            value['legs'] = []
        elif defect == 'duplicate':
            return [value, value]
        elif defect == 'shape':
            return {'results': [value]}
        elif defect == 'unknown_currency':
            value['fare']['currency'] = 'XXX'
        elif defect == 'wrong_party':
            value['travellers'] = {'adults': 1}
        return [value]

    client.app.state.fare_service = FareService(provider=Stub(respond))
    response = client.post('/flights/search', json=query)
    assert response.status_code == 502
    assert response.json()['detail']['code'] == 'invalid_response'
    assert 'results' not in response.json()


@pytest.mark.parametrize(('code', 'status'), [('authentication', 503), ('quota', 429), ('rate_limit', 429), ('unavailable', 502)])
def test_provider_errors_have_safe_messages(client, query, code, status):
    def respond(request):
        raise FareError(code)

    client.app.state.fare_service = FareService(provider=Stub(respond))
    response = client.post('/flights/search', json=query)
    assert response.status_code == status
    assert response.json()['detail']['code'] == code
    assert 'results' not in response.json()


def test_timeout_and_unexpected_adapter_failure(client, query, caplog):
    class Delayed(Stub):
        async def search(self, request):
            await asyncio.sleep(1)

    class BadRouteLookup(Stub):
        def supports_route(self, request):
            raise OSError('private-provider-detail')

    client.app.state.fare_service = FareService(provider=Delayed(None), timeout_seconds=0.01)
    assert client.post('/flights/search', json=query).json()['detail']['code'] == 'timeout'
    client.app.state.fare_service = FareService(provider=BadRouteLookup(None))
    response = client.post('/flights/search', json=query)
    assert response.status_code == 502
    assert 'private-provider-detail' not in response.text + caplog.text


def test_validated_model_routing_and_provider_fallback(client, query):
    def estimate(request):
        value = quote(request)
        value.pop('legs')
        value.pop('availability')
        value['fare']['fees'] = 'included'
        return [value | {'source': 'ml_estimate', 'origin': request.origin, 'destination': request.destination,
                         'departure_date': request.departure_date, 'return_date': request.return_date,
                         'evaluation_reference': 'test-only-reviewed-time-holdout'}]

    model = Stub(estimate)
    provider = Stub(lambda request: [quote(request)])
    client.app.state.fare_service = FareService(provider=provider, model=model, provider_cache_seconds=60)
    assert client.post('/flights/search', json=query).json()['estimation_method'] == 'historical_ml'
    assert provider.requests == []
    model.route_supported = False
    assert client.post('/flights/estimate', json=query).json()['estimation_method'] == 'market_reference'
    model.route_supported = True
    both = client.post('/flights/estimate', json=query).json()
    assert both['estimation_method'] == 'historical_ml' and both['source_status']['market'] == 'available'
    assert len(provider.requests) == 1
    model.respond = lambda request: []
    assert client.post('/flights/search', json=query).json()['estimation_method'] == 'market_reference'

def test_only_eligible_observations_are_cached_and_expire(client, query, monkeypatch):
    from backend.app import fare_service

    clock = [0.0]
    monkeypatch.setattr(fare_service, 'monotonic', lambda: clock[0])
    currency = ['USD']

    def offers(request):
        value = quote(request)
        value['fare']['currency'] = currency[0]
        return [value]

    provider = Stub(offers)
    client.app.state.fare_service = FareService(provider=provider, provider_cache_seconds=60)
    assert client.post('/flights/estimate', json=query).json()['estimation_method'] == 'unavailable'
    currency[0] = 'INR'
    assert client.post('/flights/estimate', json=query).json()['estimation_method'] == 'market_reference'
    assert len(provider.requests) == 2
    clock[0] += 59
    assert client.post('/flights/estimate', json=query).json()['estimation_method'] == 'market_reference'
    assert len(provider.requests) == 2
    clock[0] += 1
    provider.respond = lambda _: []
    empty = client.post('/flights/estimate', json=query).json()
    assert empty['estimation_method'] == 'unavailable' and empty['estimated_low'] is None
    assert len(provider.requests) == 3
