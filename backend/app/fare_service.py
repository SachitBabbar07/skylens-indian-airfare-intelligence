"""Select a validated fare source and validate the complete response before display."""

import asyncio
import logging
from datetime import datetime, timedelta, timezone
from typing import Literal

from pydantic import ValidationError

from backend.app.flight_fares import (
    FlightSearch, IST, LiveFareProvider, LiveQuote, ModelEstimate, SearchResponse, ValidatedFareModel,
)


log = logging.getLogger(__name__)
ErrorCode = Literal['unconfigured', 'unsupported', 'authentication', 'quota', 'rate_limit',
                    'timeout', 'unavailable', 'invalid_response']
ERRORS: dict[ErrorCode, tuple[int, str]] = {
    'unconfigured': (503, 'Live fare search needs a connected flight-fare provider.'),
    'unsupported': (422, 'The selected journey is outside the available fare sources’ coverage.'),
    'authentication': (503, 'The flight-fare provider could not authenticate. Check the server configuration.'),
    'quota': (429, 'The flight-fare provider’s search allowance has been reached.'),
    'rate_limit': (429, 'The flight-fare provider is busy. Wait a moment and try again.'),
    'timeout': (504, 'The flight-fare provider took too long to respond. Try again.'),
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
                 timeout_seconds: float = 10):
        # Source registration is server code. No configuration can promote the
        # existing research artifacts to a validated customer model.
        self.provider = provider
        self.model = model
        self.timeout_seconds = timeout_seconds

    def capabilities(self) -> dict:
        return {
            'live_quotes': self.provider.support if self.provider else None,
            'ml_estimates': self.model.support if self.model else None,
            'today': datetime.now(IST).date(),
        }

    async def estimate_with_model(self, request: FlightSearch) -> SearchResponse | None:
        results = await self._search_source(self.model, ModelEstimate, request)
        return SearchResponse(results=results) if results else None

    async def search(self, request: FlightSearch) -> SearchResponse:
        if self.model is None and self.provider is None:
            raise FareError('unconfigured')
        searched = False
        for source, result_type in ((self.model, ModelEstimate), (self.provider, LiveQuote)):
            results = await self._search_source(source, result_type, request)
            searched = searched or results is not None
            if results:
                return SearchResponse(results=results)
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
