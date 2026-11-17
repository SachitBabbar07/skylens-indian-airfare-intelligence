"""Experimental Groq estimates, independent of live quotes and trained research models."""

import asyncio
import json
import logging
import os
import sqlite3
from dataclasses import dataclass, field
from datetime import date, datetime, timezone
from hashlib import sha256
from pathlib import Path
from time import monotonic, time
from typing import Annotated, Literal

from dotenv import dotenv_values
from groq import APIError, APIResponseValidationError, APIStatusError, APITimeoutError, AsyncGroq
from httpx import AsyncClient
from pydantic import AwareDatetime, Field, ValidationError, model_validator

from backend.app.fare_cache import FareCache, SavedRange
from backend.app.flight_fares import DOMESTIC_AIRLINES, Cabin, Contract, FlightSearch, IATA, IST, Journey, SearchSupport


LOG = logging.getLogger(__name__)
DEFAULT_MODEL = 'openai/gpt-oss-20b'
# The SDK adds /openai/v1 to API routes. Pin the host for credentialed calls.
BASE_URL = 'https://api.groq.com'
DISCLAIMER = 'AI-generated indicative estimate. Not a live airline quote or guaranteed ticket price. Actual fares may differ.'
SUPPORT = SearchSupport(journeys=['one_way', 'round_trip'], cabins=['economy', 'premium_economy', 'business'],
                        airlines=list(DOMESTIC_AIRLINES), children=True)
SYSTEM_PROMPT = (
    'Estimate a typical Indian domestic airfare budget from the route, dates, cabin, booking lead time, '
    'distance and optional airline preference. You have no live quotes or inventory. Return only the JSON '
    'range, the all-in INR total for the whole party and journey, in rounded whole rupees. The upper and '
    'lower bounds must differ by at most 25% of the upper bound. If you lack a reasonable basis for a '
    'range this narrow or for the preferred airline on this trip, set both bounds to null. '
    'Do not invent schedules or assume discounts.'
)


@dataclass(frozen=True)
class GroqSettings:
    model: str
    api_key: str = field(repr=False)
    free_plan_confirmed: bool = False

    @classmethod
    def load(cls, directory: Path) -> 'GroqSettings':
        local = dotenv_values(directory / '.env', interpolate=False)
        model = (os.getenv('GROQ_MODEL') or local.get('GROQ_MODEL') or '').strip() or DEFAULT_MODEL
        credential_source = os.environ if 'GROQ_API_KEY' in os.environ else local
        key = (credential_source.get('GROQ_API_KEY') or '').strip()
        confirmed = (credential_source.get('GROQ_FREE_PLAN_CONFIRMED') or '').strip().lower() == 'true'
        return cls(model, key, confirmed)


Rupees = Annotated[int, Field(strict=True, gt=0, le=9_007_199_254_740_991)]


class GeneratedRange(Contract):
    estimated_low: Rupees | None
    estimated_high: Rupees | None
    currency: Literal['INR']

    @model_validator(mode='after')
    def validate_bounds(self):
        low, high = self.estimated_low, self.estimated_high
        if (low is None) != (high is None) or (low is not None and high is not None and low >= high):
            raise ValueError('Expected two increasing bounds or two null bounds.')
        return self


_NULLABLE_INTEGER = {'anyOf': [{'type': 'integer'}, {'type': 'null'}]}
RESPONSE_FORMAT = {'type': 'json_schema', 'json_schema': {
    'name': 'indicative_fare', 'strict': True, 'schema': {
        'type': 'object', 'additionalProperties': False,
        'properties': {'estimated_low': _NULLABLE_INTEGER, 'estimated_high': _NULLABLE_INTEGER,
                       'currency': {'type': 'string', 'enum': ['INR']}},
        'required': list(GeneratedRange.model_fields),
    },
}}


class IndicativeEstimate(Contract):
    estimated_low: Rupees
    estimated_high: Rupees
    currency: Literal['INR'] = 'INR'
    journey_type: Journey
    origin: IATA
    destination: IATA
    departure_date: date
    return_date: date | None
    cabin_class: Cabin
    airline: str | None = None
    airline_name: str | None = None
    estimated_at: AwareDatetime
    passenger_count: Annotated[int, Field(ge=1, le=9)]
    estimation_source: Literal['groq_indicative'] = 'groq_indicative'
    disclaimer: str = DISCLAIMER


ERRORS = {
    'unconfigured': (503, True),
    'authentication': (503, False),
    'model_unavailable': (503, False),
    'unsupported': (422, False),
    'quota': (429, False),
    'rate_limit': (429, True),
    'busy': (429, True),
    'timeout': (504, True),
    'unavailable': (502, True),
    'invalid_response': (502, True),
    'no_estimate': (422, False),
}
UNAVAILABLE_MESSAGE = 'Fare estimate temporarily unavailable. Please try again.'


class EstimateError(Exception):
    def __init__(self, code: str, retry_after: int | None = None):
        self.code = code
        self.status, self.retryable = ERRORS[code]
        self.message = ('A useful fare range is unavailable for this trip. Try a different date or airline.'
                        if code == 'no_estimate' else UNAVAILABLE_MESSAGE)
        self.retry_after = retry_after
        super().__init__(self.message)


class GroqFareEstimator:
    def __init__(self, settings: GroqSettings, http_client: AsyncClient | None = None, timeout: float = 10,
                 cache_path: Path | None = None):
        self.model = settings.model
        self.timeout = timeout
        self._cache = FareCache(cache_path) if cache_path is not None else None
        self._inflight: dict[str, asyncio.Task[IndicativeEstimate]] = {}
        self._provider_lock = asyncio.Lock()
        self._cooldown_until = 0.0
        self._cooldown_reason = 'rate_limit'
        self._client = None
        if not settings.api_key:
            LOG.warning('Indicative fares disabled category=missing_key')
        elif not settings.free_plan_confirmed:
            LOG.warning('Indicative fares disabled category=free_plan_unconfirmed')
        else:
            # SDK diagnostics can log request and response internals when GROQ_LOG is enabled.
            logging.getLogger('groq').setLevel(logging.WARNING)
            self._client = AsyncGroq(api_key=settings.api_key, base_url=BASE_URL, max_retries=0, timeout=timeout,
                                     http_client=http_client or AsyncClient(follow_redirects=False, timeout=timeout))

    @property
    def support(self) -> SearchSupport | None:
        return SUPPORT if self._client is not None else None

    async def close(self) -> None:
        pending = list(self._inflight.values())
        for task in pending:
            task.cancel()
        if pending:
            await asyncio.gather(*pending, return_exceptions=True)
        if self._client is not None:
            await self._client.close()

    async def estimate(self, search: FlightSearch, distance_km: int | None) -> IndicativeEstimate:
        if not SUPPORT.accepts(search):
            raise EstimateError('unsupported')
        if self._client is None:
            raise EstimateError('unconfigured')
        context = search.model_dump(mode='json', exclude_none=True)
        key = sha256(json.dumps([self.model, SYSTEM_PROMPT, RESPONSE_FORMAT, context, distance_km],
                                sort_keys=True).encode()).hexdigest()
        task = self._inflight.get(key)
        if task is None:
            task = asyncio.create_task(self._resolve(search, distance_km, key, context))
            self._inflight[key] = task
            task.add_done_callback(lambda completed: self._clear_inflight(key, completed))
        return await asyncio.shield(task)

    async def _resolve(self, search: FlightSearch, distance_km: int | None, key: str,
                       context: dict) -> IndicativeEstimate:
        if self._cache is not None:
            try:
                saved = await asyncio.to_thread(self._cache.lookup, key, int(time()))
                if saved is not None and self._usable_range(saved[0], saved[1]):
                    return self._result(search, saved)
            except (OSError, sqlite3.Error):
                LOG.warning('Indicative fare cache could not be read')
        if self._provider_lock.locked():
            raise EstimateError('busy')
        remaining = self._cooldown_until - monotonic()
        if remaining > 0:
            raise EstimateError(self._cooldown_reason, int(remaining) + 1)
        async with self._provider_lock:
            return await self._generate(search, distance_km, key, context)

    def _clear_inflight(self, key: str, task: asyncio.Task[IndicativeEstimate]) -> None:
        self._inflight.pop(key, None)
        if not task.cancelled():
            task.exception()

    async def _generate(self, search: FlightSearch, distance_km: int | None, key: str,
                        context: dict) -> IndicativeEstimate:
        assert self._client is not None
        context['days_until_departure'] = (search.departure_date - datetime.now(IST).date()).days
        if distance_km is not None:
            context['straight_line_distance_km_each_way'] = distance_km
        if search.airline is not None:
            context.pop('airline')
            context['airline_preference'] = DOMESTIC_AIRLINES[search.airline]
        try:
            async with asyncio.timeout(self.timeout):
                response = await self._client.chat.completions.create(
                    model=self.model,
                    messages=[{'role': 'system', 'content': SYSTEM_PROMPT},
                              {'role': 'user', 'content': json.dumps(context)}],
                    max_completion_tokens=384, temperature=0, seed=1,
                    reasoning_effort='low' if self.model in {'openai/gpt-oss-20b', 'openai/gpt-oss-120b'} else None,
                    service_tier='on_demand', response_format=RESPONSE_FORMAT,
                )
            if not response.choices or response.choices[0].finish_reason != 'stop':
                LOG.warning('Groq estimate did not return a complete response')
                raise EstimateError('invalid_response')
            content = response.choices[0].message.content
            bounds = GeneratedRange.model_validate_json(content or '')
        except (APITimeoutError, TimeoutError):
            LOG.warning('Groq estimate request timed out')
            raise EstimateError('timeout') from None
        except APIStatusError as error:
            failure = self._status_error(error)
            LOG.warning('Groq estimate request failed provider_status=%d category=%s', error.status_code, failure.code)
            raise failure from None
        except (APIResponseValidationError, ValidationError, ValueError, AttributeError, TypeError):
            LOG.warning('Groq estimate response failed validation')
            raise EstimateError('invalid_response') from None
        except APIError:
            LOG.warning('Groq estimate request did not get a usable provider response')
            raise EstimateError('unavailable') from None

        low, high = bounds.estimated_low, bounds.estimated_high
        if low is None or high is None or not self._usable_range(low, high):
            raise EstimateError('no_estimate')
        estimate = low, high, int(time())
        if self._cache is not None:
            try:
                estimate = await asyncio.to_thread(self._cache.store, key, estimate)
            except (OSError, sqlite3.Error):
                LOG.warning('Indicative fare cache could not be written')
        return self._result(search, estimate)

    @staticmethod
    def _usable_range(low: int, high: int) -> bool:
        return 0 < low < high <= 9_007_199_254_740_991 and 4 * (high - low) <= high

    @staticmethod
    def _result(search: FlightSearch, saved: SavedRange) -> IndicativeEstimate:
        low, high, timestamp = saved
        return IndicativeEstimate(estimated_low=low, estimated_high=high,
                                  journey_type=search.journey, origin=search.origin, destination=search.destination,
                                  departure_date=search.departure_date, return_date=search.return_date,
                                  airline=search.airline, airline_name=DOMESTIC_AIRLINES.get(search.airline or ''),
                                  estimated_at=datetime.fromtimestamp(timestamp, timezone.utc),
                                  cabin_class=search.cabin, passenger_count=search.travellers.total)

    def _status_error(self, error: APIStatusError) -> EstimateError:
        status = error.status_code
        headers = error.response.headers
        if status == 401:
            return EstimateError('authentication')
        if status in {402, 429}:
            code = 'quota' if status == 402 or headers.get('x-ratelimit-remaining-requests') == '0' else 'rate_limit'
            raw_delay = headers.get('retry-after', '')
            delay = max(1, int(raw_delay)) if raw_delay.isascii() and raw_delay.isdigit() and len(raw_delay) <= 9 else 30
            self._cooldown_until = monotonic() + delay
            self._cooldown_reason = code
            return EstimateError(code, delay)
        if status in {400, 422}:
            body = error.body.get('error', error.body) if isinstance(error.body, dict) else None
            if isinstance(body, dict) and body.get('code') in ('json_validate_failed', 'json_schema_validation_failed'):
                return EstimateError('invalid_response')
        if status in {400, 403, 404, 422}:
            return EstimateError('model_unavailable')
        if status == 408:
            return EstimateError('timeout')
        return EstimateError('unavailable')
