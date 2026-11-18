"""Read-only fallback through Kiwi.com's public flight-search MCP endpoint."""

import asyncio
import json
import logging
import os
import re
import ssl
import sys
from datetime import datetime, timezone
from decimal import Decimal
from itertools import count

import httpx

from backend.app.fare_service import FareError
from backend.app.flight_fares import DOMESTIC_AIRLINES, IST, Fare, FlightLeg, FlightSearch, LiveQuote, SearchSupport


KIWI_URL = 'https://mcp.kiwi.com'
MAX_RESPONSE_BYTES = 2_000_000
LOG = logging.getLogger(__name__)
AIRLINE_CODES = {
    'air_india': 'AI', 'air_india_express': 'IX', 'akasa_air': 'QP', 'alliance_air': '9I', 'fly91': 'IC',
    'indiaone_air': 'I7', 'indigo': '6E', 'spicejet': 'SG', 'star_air': 'S5',
}
AIRLINE_NAMES = {code: DOMESTIC_AIRLINES[key] for key, code in AIRLINE_CODES.items()}
CABINS = {
    'economy': ('M', {'economy'}), 'premium_economy': ('W', {'premium economy'}),
    'business': ('C', {'business', 'business class'}), 'first': ('F', {'first', 'first class'}),
}


class KiwiFareProvider:
    support = SearchSupport(journeys=['one_way', 'round_trip'],
                            cabins=['economy', 'premium_economy', 'business', 'first'],
                            children=True, infants=True, airlines=list(AIRLINE_CODES))

    def __init__(self, client: httpx.AsyncClient | None = None):
        if client is None:
            verify = (ssl.create_default_context() if sys.platform == 'win32'
                      and not (os.getenv('SSL_CERT_FILE') or os.getenv('SSL_CERT_DIR')) else True)
            client = httpx.AsyncClient(verify=verify, timeout=10, follow_redirects=False,
                                       limits=httpx.Limits(keepalive_expiry=60))
        self.client = client
        self._init_lock = asyncio.Lock()
        self._initialized = False
        self._ids = count(1)
        self._headers = {'Accept': 'application/json, text/event-stream'}

    def supports_route(self, request: FlightSearch) -> bool:
        # The calling endpoint validates the IATA codes against the Indian airport directory.
        return request.travellers.infants <= 4

    async def close(self) -> None:
        await self.client.aclose()

    async def _initialize(self) -> None:
        async with self._init_lock:
            if self._initialized:
                return
            self._headers = {'Accept': 'application/json, text/event-stream'}
            init = await self._rpc('initialize', {'protocolVersion': '2025-03-26', 'capabilities': {},
                                                'clientInfo': {'name': 'SkyLens', 'version': '0.1.0'}})
            version = init.get('protocolVersion')
            if not isinstance(version, str) or not re.fullmatch(r'\d{4}-\d{2}-\d{2}', version):
                raise FareError('invalid_response')
            self._headers['MCP-Protocol-Version'] = version
            await self._rpc('notifications/initialized', notification=True)
            self._initialized = True

    async def _rpc(self, method: str, params: dict | None = None, *, notification: bool = False) -> dict:
        request_id = next(self._ids)
        message = {'jsonrpc': '2.0', 'method': method}
        if params is not None:
            message['params'] = params
        if not notification:
            message['id'] = request_id
        try:
            async with self.client.stream('POST', KIWI_URL, headers=self._headers, json=message) as response:
                if response.status_code == 404 and method != 'initialize':
                    self._initialized = False
                if not response.is_success:
                    codes = {401: 'authentication', 402: 'quota', 429: 'rate_limit'}
                    LOG.warning('Kiwi fare service rejected operation=%s HTTP=%d', method, response.status_code)
                    raise FareError(codes.get(response.status_code, 'unavailable'))
                if method == 'initialize' and (session := response.headers.get('Mcp-Session-Id')):
                    self._headers['Mcp-Session-Id'] = session
                # Kiwi ends each POST response after the reply. Drain it so httpx
                # can reuse the verified TLS connection for the search itself.
                body = bytearray()
                async for chunk in response.aiter_bytes():
                    body.extend(chunk)
                    if len(body) > MAX_RESPONSE_BYTES:
                        raise FareError('invalid_response')
                if notification and response.status_code == 202:
                    return {}
                envelope = _decode_reply(body, response.headers.get('Content-Type', ''), request_id)
        except httpx.TimeoutException:
            LOG.warning('Kiwi fare service timed out operation=%s', method)
            raise FareError('timeout') from None
        except httpx.HTTPError as error:
            if 'CERTIFICATE_VERIFY_FAILED' in str(error):
                LOG.warning('Kiwi fare transport failed operation=%s category=tls_verification', method)
                raise FareError('tls_verification') from None
            LOG.warning('Kiwi fare transport failed operation=%s category=%s', method, type(error).__name__)
            raise FareError('unavailable') from None
        except (ValueError, TypeError):
            raise FareError('invalid_response') from None
        if 'error' in envelope:
            raise FareError('unavailable')
        result = envelope.get('result')
        if not isinstance(result, dict):
            raise FareError('invalid_response')
        return result

    async def search(self, request: FlightSearch) -> list[LiveQuote]:
        await self._initialize()
        carrier = AIRLINE_CODES.get(request.airline)
        cabin_code, cabin_labels = CABINS[request.cabin]
        args = {'flyFrom': request.origin, 'flyTo': request.destination,
                'departureDate': request.departure_date.strftime('%d/%m/%Y'), 'departureDateFlexDays': 0,
                **request.travellers.model_dump(), 'cabinClass': cabin_code, 'currency': 'INR', 'locale': 'en',
                'allow_self_transfer': False, 'allow_diff_airport_connection': False}
        if carrier:
            args['select_airlines'] = carrier
        if request.return_date:
            args.update(returnDate=request.return_date.strftime('%d/%m/%Y'), returnDateFlexDays=0)
        result = await self._rpc('tools/call', {'name': 'search-flight', 'arguments': args})
        data = result.get('structuredContent')
        if result.get('isError') or not isinstance(data, dict):
            raise FareError('invalid_response')
        if data.get('error'):
            raise FareError('unavailable')
        if (data.get('currency') != 'INR' or data.get('passengers') != request.travellers.model_dump()
                or not isinstance(data.get('itineraries'), list)):
            raise FareError('invalid_response')
        retrieved = datetime.now(timezone.utc)
        quotes = {}
        for entry in data['itineraries']:
            try:
                quote = _quote(entry, request, retrieved, carrier, cabin_labels)
            except (ValueError, KeyError, TypeError, AttributeError):
                continue
            quotes.setdefault(quote.id, quote)
        if data['itineraries'] and not quotes:
            raise FareError('invalid_response')
        return list(quotes.values())


def _decode_reply(body: bytearray, content_type: str, request_id: int) -> dict:
    if content_type.startswith('text/event-stream'):
        lines = []
        for line in body.decode('utf-8').splitlines():
            if line.startswith('data:'):
                lines.append(line[5:].removeprefix(' '))
            if not line and lines:
                message = json.loads('\n'.join(lines), parse_float=Decimal)
                if isinstance(message, dict) and message.get('id') == request_id:
                    return message
                lines.clear()
    else:
        message = json.loads(body, parse_float=Decimal)
        if isinstance(message, dict) and message.get('id') == request_id:
            return message
    raise FareError('invalid_response')


def _quote(entry: dict, request: FlightSearch, retrieved: datetime, carrier: str | None,
           cabins: set[str]) -> LiveQuote:
    is_return = request.journey == 'round_trip'
    if entry['tripType'] != ('return' if is_return else 'oneway') or bool(entry.get('inbound')) != is_return:
        raise ValueError('Trip type mismatch')
    legs = [_leg(entry['outbound'], carrier, cabins)]
    if is_return:
        legs.append(_leg(entry['inbound'], carrier, cabins))
    actual = [(leg.origin, leg.destination, leg.departure.astimezone(IST).date()) for leg in legs]
    expected = [(request.origin, request.destination, request.departure_date)]
    if is_return:
        expected.append((request.destination, request.origin, request.return_date))
    if actual != expected or (is_return and legs[1].departure < legs[0].arrival):
        raise ValueError('Requested itinerary mismatch')
    price = entry['price']
    if type(price) not in (int, Decimal):
        raise ValueError('Expected structured numerical price')
    return LiveQuote(id=entry['id'], source='live_quote', source_name='Kiwi.com', availability='available',
                     retrieved_at=retrieved, journey=request.journey, cabin=request.cabin, travellers=request.travellers,
                     legs=legs, fare=Fare(amount=price, currency='INR', basis='party_total', taxes='unknown', fees='unknown'))


def _local_time(value: str) -> datetime:
    parsed = datetime.fromisoformat(value)
    return parsed if parsed.tzinfo is not None else parsed.replace(tzinfo=IST)


def _leg(value: dict, carrier: str | None, cabins: set[str]) -> FlightLeg:
    segments = value['segments']
    if (not isinstance(segments, list) or not segments or value['cabinClass'].casefold() not in cabins
            or value['stops'] != len(segments) - 1):
        raise ValueError('Incomplete itinerary')
    airlines = []
    flight_numbers = []
    previous_airport = value['from']
    start = _local_time(value['departureTime'])
    end = _local_time(value['arrivalTime'])
    for segment in segments:
        code = segment['carrier']
        flight = segment['flightNumber'].replace(' ', '')
        if (segment['from'] != previous_airport or segment['fromCountry'] != 'India' or segment['toCountry'] != 'India'
                or segment['cabinClass'].casefold() not in cabins or (carrier is not None and code != carrier)
                or not re.fullmatch(r'[A-Z0-9]{2}', code) or not re.fullmatch(r'[A-Z0-9]{2,12}', flight)):
            raise ValueError('Unsupported segment')
        airlines.append(AIRLINE_NAMES.get(code, segment.get('carrierName') or code))
        flight_numbers.append(flight)
        previous_airport = segment['to']
    if (previous_airport != value['to'] or _local_time(segments[0]['departureTime']) != start
            or _local_time(segments[-1]['arrivalTime']) != end):
        raise ValueError('Segment endpoints disagree')
    return FlightLeg(origin=value['from'], destination=value['to'], departure=start, arrival=end,
                     airlines=list(dict.fromkeys(airlines)), flight_numbers=flight_numbers, stops=value['stops'],
                     duration_minutes=round((end - start).total_seconds() / 60))
