"""Select a validated fare source and validate the complete response before display."""

import asyncio
import logging
from collections import OrderedDict
from datetime import datetime, timedelta, timezone
from time import monotonic
from typing import Literal

from pydantic import ValidationError

from backend.app.flight_fares import (
    FlightSearch, IST, LiveFareProvider, LiveQuote, ModelEstimate, SearchResponse, ValidatedFareModel,
)


log = logging.getLogger(__name__)
ErrorCode = Literal['unconfigured', 'unsupported', 'authentication', 'quota', 'rate_limit',
                    'timeout', 'tls_verification', 'unavailable', 'invalid_response']
ERRORS: dict[ErrorCode, tuple[int, str]] = {
    'unconfigured': (503, 'Live fare search needs a connected flight-fare provider.'),
    'unsupported': (422, 'The selected journey is outside the available fare sources’ coverage.'),
    'authentication': (503, 'The flight-fare provider could not authenticate. Check the server configuration.'),
    'quota': (429, 'The flight-fare provider’s search allowance has been reached.'),
    'rate_limit': (429, 'The flight-fare provider is busy. Wait a moment and try again.'),
    'timeout': (504, 'The flight-fare provider took too long to respond. Try again.'),
    'tls_verification': (502, 'This computer could not verify the fare provider’s HTTPS certificate. Try again.'),
    'unavailable': (502, 'The flight-fare provider is temporarily unavailable. Try again.'),
    'invalid_response': (502, 'The flight-fare provider sent incomplete or inconsistent results. Try again.'),
}


class FareError(Exception):
    def __init__(self, code: ErrorCode):
        self.code = code
        self.status, self.message = ERRORS[code]
        super().__init__(self.message)


class FareService:
    def __init__(self, provider: LiveFareProvider | None = None, model: ValidatedFareModel | None = None,
                 timeout_seconds: float = 10, provider_cache_seconds: float = 0):
        # Source registration is server code. No configuration can promote the
        # existing research artifacts to a validated customer model.
        self.provider = provider
        self.model = model
        self.timeout_seconds = timeout_seconds
        self.provider_cache_seconds = provider_cache_seconds
        self._recent_quotes: OrderedDict[str, tuple[float, SearchResponse]] = OrderedDict()

    def capabilities(self) -> dict:
        return {
            'live_quotes': self.provider.support if self.provider else None,
            'ml_estimates': self.model.support if self.model else None,
            'today': datetime.now(IST).date(),
        }

    async def search(self, request: FlightSearch) -> SearchResponse:
        if self.model is None and self.provider is None:
            raise FareError('unconfigured')
        searched = False
        for source, result_type in ((self.model, ModelEstimate), (self.provider, LiveQuote)):
            cache_key = request.model_dump_json() if result_type is LiveQuote and self.provider_cache_seconds > 0 else None
            if cache_key is not None and (saved := self._recent_quotes.pop(cache_key, None)):
                if saved[0] > monotonic():
                    self._recent_quotes[cache_key] = saved
                    return saved[1]
            results = await self._search_source(source, result_type, request)
            searched = searched or results is not None
            if results:
                response = SearchResponse(results=results)
                if cache_key is not None:
                    self._recent_quotes[cache_key] = (monotonic() + self.provider_cache_seconds, response)
                    if len(self._recent_quotes) > 64:
                        self._recent_quotes.popitem(last=False)
                return response
        if not searched:
            raise FareError('unsupported')
        return SearchResponse(results=[])

    async def _search_source(self, source: LiveFareProvider | ValidatedFareModel | None,
                             result_type: type[LiveQuote] | type[ModelEstimate], request: FlightSearch
                             ) -> list[LiveQuote | ModelEstimate] | None:
        if source is None:
            return None
        try:
            if not source.support.accepts(request) or not source.supports_route(request):
                return None
            started = datetime.now(timezone.utc)
            async with asyncio.timeout(self.timeout_seconds):
                values = await source.search(request)
            if not isinstance(values, list):
                raise FareError('invalid_response')
            results = [result_type.model_validate(value.model_dump() if isinstance(value, result_type) else value)
                       for value in values]
            if len({value.id for value in results}) != len(results):
                raise FareError('invalid_response')
            for value in results:
                self._verify_result(value, request, started)
            return results
        except TimeoutError:
            raise FareError('timeout') from None
        except ValidationError:
            raise FareError('invalid_response') from None
        except FareError:
            raise
        except Exception:
            # Adapter exceptions can contain a credential-bearing URL or provider payload.
            log.warning('Fare source request failed')
            raise FareError('unavailable') from None

    @staticmethod
    def _verify_result(value: LiveQuote | ModelEstimate, request: FlightSearch, started: datetime) -> None:
        if (value.journey != request.journey or value.cabin != request.cabin
                or value.travellers != request.travellers
                or not started - timedelta(seconds=2) <= value.retrieved_at <= datetime.now(timezone.utc) + timedelta(seconds=2)):
            raise FareError('invalid_response')
        if isinstance(value, LiveQuote):
            expected_legs = [(request.origin, request.destination, request.departure_date)]
            if request.journey == 'round_trip':
                expected_legs.append((request.destination, request.origin, request.return_date))
            actual_legs = [(leg.origin, leg.destination, leg.departure.astimezone(IST).date()) for leg in value.legs]
            if actual_legs != expected_legs or (len(value.legs) == 2 and value.legs[1].departure < value.legs[0].arrival):
                raise FareError('invalid_response')
