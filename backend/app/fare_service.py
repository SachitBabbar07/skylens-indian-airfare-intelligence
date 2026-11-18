"""Route a fare request to validated model evidence or comparable market observations."""

import asyncio
import logging
from collections import OrderedDict
from datetime import datetime, timedelta, timezone
from time import monotonic
from typing import Literal, TypeVar

from pydantic import ValidationError

from backend.app.flight_fares import IST, FlightSearch, LiveFareProvider, LiveQuote, ValidatedFareModel, ValidatedModelEstimate
from backend.app.hybrid_estimator import EstimateResponse, select_estimate


log = logging.getLogger(__name__)
T = TypeVar('T', LiveQuote, ValidatedModelEstimate)
ErrorCode = Literal['unconfigured', 'unsupported', 'authentication', 'quota', 'rate_limit',
                    'timeout', 'tls_verification', 'unavailable', 'invalid_response']
ERRORS: dict[ErrorCode, tuple[int, str]] = {
    'unconfigured': (503, 'No fare source is configured.'),
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
        self.provider = provider
        # Only reviewed customer adapters may be registered here. Research models
        # use a separate store and have no customer target or evaluation approval.
        self.model = model
        self.timeout_seconds = timeout_seconds
        self.provider_cache_seconds = provider_cache_seconds
        self._recent_quotes: OrderedDict[str, tuple[float, list[LiveQuote]]] = OrderedDict()

    def capabilities(self) -> dict:
        return {
            'live_quotes': self.provider.support if self.provider else None,
            'ml_estimates': self.model.support if self.model else None,
            'today': datetime.now(IST).date(),
        }

    def _cached_quotes(self, key: str) -> list[LiveQuote] | None:
        entry = self._recent_quotes.pop(key, None)
        if entry is None or entry[0] <= monotonic():
            return None
        self._recent_quotes[key] = entry
        return entry[1]

    async def estimate(self, request: FlightSearch) -> EstimateResponse:
        key = request.model_dump_json()
        quotes = self._cached_quotes(key)
        market_status = 'available' if quotes else 'not_requested'
        model = None
        coverage = 'unsupported'
        model_status = 'unsupported'
        model_error = None
        if self.model is not None:
            try:
                candidates = await self._search_source(self.model, ValidatedModelEstimate, request)
                if candidates:
                    if len(candidates) != 1:
                        raise FareError('invalid_response')
                    model = candidates[0]
                    coverage = 'validated'
                    model_status = 'available'
            except FareError as exc:
                model_error = exc
                coverage, model_status = 'unavailable', exc.code

        decision = select_estimate(request, model, quotes or [], coverage_status=coverage,
                                   model_status=model_status, market_status=market_status)
        if decision.response.estimation_method != 'unavailable':
            if decision.model_value is not None and decision.market_reference is not None:
                log.info('Fare selection method=%s model_amount=%s model_currency=%s market_median=%s '
                         'market_currency=%s comparable=%s', decision.response.estimation_method,
                         decision.model_value.amount, decision.model_value.currency, decision.market_reference.median,
                         decision.market_reference.currency, decision.comparable)
            return decision.response
        if self.provider is None:
            if model_error:
                raise model_error
            if self.model is None:
                raise FareError('unconfigured')
            market_status = 'unconfigured'
        elif quotes is None:
            quotes = await self._search_source(self.provider, LiveQuote, request)
            market_status = ('unsupported' if quotes is None else 'no_observations' if not quotes else 'available')
        decision = select_estimate(request, model, quotes or [], coverage_status=coverage,
                                   model_status=model_status, market_status=market_status)
        if (quotes and self.provider_cache_seconds > 0 and key not in self._recent_quotes
                and decision.response.estimation_method == 'market_reference'):
            self._recent_quotes[key] = (monotonic() + self.provider_cache_seconds, quotes)
            if len(self._recent_quotes) > 64:
                self._recent_quotes.popitem(last=False)
        return decision.response

    async def _search_source(self, source: LiveFareProvider | ValidatedFareModel, result_type: type[T],
                             request: FlightSearch) -> list[T] | None:
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
            # Adapter exceptions can contain credentials or private provider payloads.
            log.warning('Fare source request failed')
            raise FareError('unavailable') from None

    @staticmethod
    def _verify_result(value: LiveQuote | ValidatedModelEstimate, request: FlightSearch, started: datetime) -> None:
        if (value.journey != request.journey or value.cabin != request.cabin
                or value.travellers != request.travellers
                or not started - timedelta(seconds=2) <= value.retrieved_at <= datetime.now(timezone.utc) + timedelta(seconds=2)):
            raise FareError('invalid_response')
        if isinstance(value, LiveQuote):
            expected = [(request.origin, request.destination, request.departure_date)]
            if request.journey == 'round_trip':
                expected.append((request.destination, request.origin, request.return_date))
            actual = [(leg.origin, leg.destination, leg.departure.astimezone(IST).date()) for leg in value.legs]
            if actual != expected or (len(value.legs) == 2 and value.legs[1].departure < value.legs[0].arrival):
                raise FareError('invalid_response')
