"""Exercise fare normalization through Kiwi's HTTP adapter with synthetic responses."""

import asyncio
import json
from copy import deepcopy
from datetime import datetime, timedelta

import httpx
import pytest

from backend.app.fare_service import FareError
from backend.app.flight_fares import FlightSearch, IST
from backend.app.kiwi_fares import KiwiFareProvider


@pytest.fixture
def sample():
    day = datetime.now(IST).date() + timedelta(days=7)
    query = FlightSearch(origin='DEL', destination='BOM', departure_date=day, journey='one_way')

    def segment(origin, destination, departure, arrival, number):
        return {'from': origin, 'to': destination, 'fromCountry': 'India', 'toCountry': 'India',
                'carrier': 'AI', 'flightNumber': number, 'cabinClass': 'Economy',
                'departureTime': f'{day}T{departure}', 'arrivalTime': f'{day}T{arrival}'}

    first = segment('DEL', 'AMD', '08:00:00', '09:00:00', 'AI101')
    second = segment('AMD', 'BOM', '10:00:00', '11:00:00', 'AI102')
    leg = {'from': 'DEL', 'to': 'BOM', 'cabinClass': 'Economy', 'stops': 1,
           'route': ['DEL', 'AMD', 'BOM'], 'departureTime': first['departureTime'],
           'arrivalTime': second['arrivalTime'], 'segments': [first, second]}
    item = {'id': 'fixture-one', 'tripType': 'oneway', 'price': 8000, 'outbound': leg}
    document = {'currency': 'INR', 'passengers': {'adults': 1, 'children': 0, 'infants': 0},
                'itineraries': [item]}
    return query, document


def search(query, document):
    def respond(request):
        rpc = json.loads(request.content)
        if rpc['method'] == 'notifications/initialized':
            return httpx.Response(202)
        if rpc['method'] == 'initialize':
            result = {'protocolVersion': '2025-03-26'}
        else:
            assert rpc['method'] == 'tools/call'
            result = {'structuredContent': document, 'isError': False}
        return httpx.Response(200, json={'jsonrpc': '2.0', 'id': rpc['id'], 'result': result})

    async def run():
        async with httpx.AsyncClient(transport=httpx.MockTransport(respond)) as client:
            return await KiwiFareProvider(client).search(query)

    return asyncio.run(run())


def assert_invalid(query, document):
    with pytest.raises(FareError) as failure:
        search(query, document)
    assert failure.value.code == 'invalid_response'


@pytest.mark.parametrize(('category', 'value'), [('adults', True), ('infants', False), ('adults', 1.0)])
def test_passenger_echo_requires_integer_counts(sample, category, value):
    query, document = sample
    document['passengers'][category] = value
    assert_invalid(query, document)


@pytest.mark.parametrize(('field', 'value'), [('currency', 'USD'), ('priceBasis', 'per_passenger'),
                                               ('priceScope', 'per_leg')])
def test_per_offer_monetary_fields_cannot_contradict_request(sample, field, value):
    query, document = sample
    document['itineraries'][0][field] = value
    assert_invalid(query, document)


def test_identical_duplicate_is_one_observation(sample):
    query, document = sample
    document['itineraries'].append(deepcopy(document['itineraries'][0]))
    quotes = search(query, document)
    assert [(quote.id, quote.fare.amount) for quote in quotes] == [('fixture-one', 8000)]


def test_duplicate_id_with_conflicting_prices_is_rejected(sample):
    query, document = sample
    document['itineraries'].append({**document['itineraries'][0], 'price': 6000})
    assert_invalid(query, document)


@pytest.mark.parametrize(('segment', 'field', 'clock'), [
    (1, 'departureTime', '08:50:00'),  # Departs before the connection arrives.
    (0, 'arrivalTime', '07:55:00'),  # Arrives before this segment departs.
])
def test_connection_times_are_chronologically_consistent(sample, segment, field, clock):
    query, document = sample
    document['itineraries'][0]['outbound']['segments'][segment][field] = f'{query.departure_date}T{clock}'
    assert_invalid(query, document)


@pytest.mark.parametrize('value', [True, '1', 1.0, 0.5, -1])
def test_stop_count_is_a_nonnegative_json_integer(sample, value):
    query, document = sample
    document['itineraries'][0]['outbound']['stops'] = value
    assert_invalid(query, document)
