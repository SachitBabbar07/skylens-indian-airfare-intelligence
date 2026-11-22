"""Select one customer fare from a validated model or comparable observed itineraries."""

from collections import defaultdict
from collections.abc import Sequence
from dataclasses import dataclass
from datetime import date, timezone
from decimal import Decimal
from typing import Annotated, Literal

from pydantic import Field, PlainSerializer

from backend.app.flight_fares import (
    DOMESTIC_AIRLINES, IATA, IST, Cabin, Contract, Fare, FlightSearch, Journey, LiveQuote, ValidatedModelEstimate,
)


CoverageStatus = Literal['validated', 'unsupported', 'unavailable']
Treatment = Literal['included', 'excluded', 'unknown']
Scope = Literal['party_total']
Amount = Annotated[Decimal, PlainSerializer(lambda value: format(value, 'f'), return_type=str, when_used='json')]
# Require at least two observations per quarter before describing the middle half
# of a sample. This is a reporting threshold, not a coverage guarantee.
MIN_BAND_SAMPLE = 8


class SourceStatus(Contract):
    model: str
    market: str


class MarketStatistics(Contract):
    input_quote_count: int
    selected_quote_count: int
    observed_min: Amount
    observed_max: Amount
    outlier_count: int | None
    duration_min_minutes: list[int]
    duration_max_minutes: list[int]


class EstimateResponse(Contract):
    estimated_low: Amount | None
    estimated_median: Amount | None
    estimated_high: Amount | None
    currency: Literal['INR'] | None
    origin: IATA
    destination: IATA
    departure_date: date
    return_date: date | None
    journey_type: Journey
    passenger_count: Annotated[int, Field(ge=1, le=9)]
    cabin_class: Cabin
    estimation_method: Literal['historical_ml', 'market_reference', 'unavailable']
    coverage_status: CoverageStatus
    source_status: SourceStatus
    price_scope: Scope | None
    taxes: Treatment | None
    fees: Treatment | None
    observation_count: Annotated[int, Field(ge=0)]
    range_kind: Literal['point', 'limited_sample', 'interquartile', 'unavailable']
    stop_profile: list[int] | None
    market_statistics: MarketStatistics | None
    disclaimer: str


class MarketReference(Contract):
    low: Decimal | None
    median: Decimal
    high: Decimal | None
    currency: str
    price_scope: Scope
    taxes: Treatment
    fees: Treatment
    observation_count: int
    stop_profile: list[int]
    statistics: MarketStatistics


@dataclass(frozen=True)
class EstimateDecision:
    response: EstimateResponse
    model_value: Fare | None
    market_reference: MarketReference | None
    comparable: bool


def select_estimate(
    request: FlightSearch, model: ValidatedModelEstimate | None, quotes: Sequence[LiveQuote], *,
    coverage_status: CoverageStatus, market_status: str, model_status: str | None = None,
) -> EstimateDecision:
    """Apply reviewed coverage first, then a market summary. No learned weights are available."""
    model_value = None
    if model is not None:
        if (coverage_status == 'validated' and isinstance(model, ValidatedModelEstimate)
                and _matches_model(request, model)):
            model_value = model.fare
            model_status = 'available'
        else:
            model_status = 'invalid_response'
            if coverage_status == 'validated':
                coverage_status = 'unavailable'

    reference, comparable = _select_market(request, quotes, model if model_value is not None else None)
    market_eligible = reference is not None and reference.currency == 'INR'
    if market_eligible:
        market_status = 'available'
    elif quotes:
        market_status = 'incompatible_observations'
    elif market_status == 'available':
        market_status = 'no_observations'

    observations = 0
    stop_profile = statistics = None
    if model_value is not None:
        method = 'historical_ml'
        range_kind = 'point'
        low = median = high = model_value.amount
        scope, taxes, fees = model_value.basis, model_value.taxes, model_value.fees
        disclaimer = 'Historical model estimate for the full party. The booking price can change.'
    elif market_eligible:
        method = 'market_reference'
        low, median, high = reference.low, reference.median, reference.high
        scope, taxes, fees = reference.price_scope, reference.taxes, reference.fees
        observations = reference.observation_count
        stop_profile, statistics = reference.stop_profile, reference.statistics
        if low is None:
            range_kind = 'limited_sample'
            disclaimer = ('Full-party market reference from one observed itinerary.' if observations == 1 else
                          f'Median full-party fare across {observations} comparable itineraries.')
            disclaimer += ' Too few itineraries were observed to report an indicative range.'
        else:
            range_kind = 'interquartile'
            disclaimer = f'The range covers the middle half of full-party fares across {observations} comparable itineraries.'
        disclaimer += ' The booking price can change.'
    else:
        method = 'unavailable'
        range_kind = 'unavailable'
        low = median = high = scope = taxes = fees = None
        disclaimer = 'A reliable fare estimate is unavailable for this search.'

    if taxes == 'unknown' and fees == 'unknown':
        disclaimer += ' Tax and fee inclusion is unknown.'
    else:
        if taxes == 'unknown':
            disclaimer += ' Tax inclusion is unknown.'
        elif taxes == 'excluded':
            disclaimer += ' Taxes are excluded.'
        if fees == 'unknown':
            disclaimer += ' Fee inclusion is unknown.'
        elif fees == 'excluded':
            disclaimer += ' Fees are excluded.'

    response = EstimateResponse(
        estimated_low=low, estimated_median=median, estimated_high=high, currency='INR' if median is not None else None,
        origin=request.origin, destination=request.destination, departure_date=request.departure_date,
        return_date=request.return_date, journey_type=request.journey, passenger_count=request.travellers.total,
        cabin_class=request.cabin, estimation_method=method, coverage_status=coverage_status,
        source_status=SourceStatus(model=model_status or coverage_status, market=market_status),
        price_scope=scope, taxes=taxes, fees=fees, observation_count=observations, range_kind=range_kind,
        stop_profile=stop_profile, market_statistics=statistics, disclaimer=disclaimer)
    return EstimateDecision(response, model_value, reference, comparable)


def _matches_model(request: FlightSearch, model: ValidatedModelEstimate) -> bool:
    return (
        model.origin == request.origin and model.destination == request.destination
        and model.departure_date == request.departure_date and model.return_date == request.return_date
        and model.journey == request.journey and model.cabin == request.cabin
        and model.travellers == request.travellers and model.airline == request.airline
        and model.fare.currency == 'INR' and 'unknown' not in (model.fare.taxes, model.fare.fees)
    )


def _matches_quote(request: FlightSearch, quote: LiveQuote) -> bool:
    if quote.journey != request.journey or quote.cabin != request.cabin or quote.travellers != request.travellers:
        return False
    actual = [(leg.origin, leg.destination, leg.departure.astimezone(IST).date()) for leg in quote.legs]
    expected = [(request.origin, request.destination, request.departure_date)]
    if request.return_date:
        expected.append((request.destination, request.origin, request.return_date))
    if actual != expected or (len(actual) == 2 and quote.legs[1].departure < quote.legs[0].arrival):
        return False
    if request.airline is not None:
        airline = DOMESTIC_AIRLINES[request.airline].casefold()
        return all(name.strip().casefold() == airline for leg in quote.legs for name in leg.airlines)
    return True


def _percentile(sorted_prices: Sequence[Decimal], fraction: Decimal) -> Decimal:
    """Type 7 sample quantile, exact decimal interpolation at (n - 1) * p."""
    index = (len(sorted_prices) - 1) * fraction
    lower = int(index)
    remainder = index - lower
    if not remainder:
        return sorted_prices[lower]
    return sorted_prices[lower] + remainder * (sorted_prices[lower + 1] - sorted_prices[lower])


@dataclass(frozen=True)
class _MarketTerms:
    currency: str
    scope: Scope
    taxes: Treatment
    fees: Treatment
    # A single adapter may leave inclusions unstated. Two independent sources
    # with unstated terms have no basis for combining their observations.
    source_with_unstated_terms: str | None


@dataclass(frozen=True)
class _Itinerary:
    price: Decimal
    listing_count: int
    durations: tuple[int, ...]


def _compatible_signatures(first: tuple, second: tuple) -> bool:
    return all(a is None or b is None or a == b for a, b in zip(first, second))


def _resolve_schedule(variants: dict[tuple, list[tuple[_MarketTerms, Decimal]]], durations: tuple[int, ...]):
    # A signature starts with stops in each direction, then flight numbers in
    # each direction. A partial record may contribute to a more specific record
    # only when all its known fields match and there is no competing identity.
    directions = len(durations)
    maximal = [key for key in variants if not any(
        key != other and all(a is None or a == b for a, b in zip(key, other)) for other in variants)]
    known = [key for key in maximal if None not in key[:directions]]
    eligible = {key for key in known if not any(
        other != key and _compatible_signatures(key, other) for other in known)}
    contributors = defaultdict(list)
    for signature, listings in variants.items():
        if signature in eligible:
            identity = signature
        else:
            matches = [key for key in maximal if _compatible_signatures(key, signature)]
            if len(matches) != 1 or matches[0] not in eligible:
                continue
            identity = matches[0]
        for terms, price in listings:
            contributors[identity, terms].append(price)
    for (identity, terms), prices in contributors.items():
        yield terms, identity[:directions], _Itinerary(
            _percentile(sorted(set(prices)), Decimal('0.5')), len(prices), durations)


def _cohorts(request: FlightSearch, quotes: Sequence[LiveQuote]):
    schedules = defaultdict(lambda: defaultdict(list))
    for quote in quotes:
        if not _matches_quote(request, quote):
            continue
        fare = quote.fare
        source = quote.source_name if 'unknown' in (fare.taxes, fare.fees) else None
        terms = _MarketTerms(fare.currency, fare.basis, fare.taxes, fare.fees, source)
        schedule = tuple(
            (leg.origin, leg.destination, leg.departure.astimezone(timezone.utc), leg.arrival.astimezone(timezone.utc),
             tuple(' '.join(name.casefold().split()) for name in leg.airlines))
            for leg in quote.legs)
        elapsed = [(arrival - departure).total_seconds() / 60 for _, _, departure, arrival, _ in schedule]
        # Accept whole minutes rounded up or down from sub-minute timestamps.
        if any(leg.duration_minutes is not None and abs(leg.duration_minutes - minutes) >= 1
               for leg, minutes in zip(quote.legs, elapsed)):
            continue
        durations = tuple(round(minutes) for minutes in elapsed)
        profile = tuple(leg.stops for leg in quote.legs)
        numbers = tuple(tuple(leg.flight_numbers) or None for leg in quote.legs)
        schedules[schedule, durations][profile + numbers].append((terms, fare.amount))

    cohorts = defaultdict(list)
    for (_, durations), variants in schedules.items():
        for terms, profile, itinerary in _resolve_schedule(variants, durations):
            cohorts[terms, profile].append(itinerary)
    return cohorts


def _summarize(terms: _MarketTerms, profile: tuple[int, ...], itineraries: list[_Itinerary],
               input_count: int) -> MarketReference:
    prices = sorted(itinerary.price for itinerary in itineraries)
    low = high = outliers = None
    if len(prices) >= MIN_BAND_SAMPLE:
        low = _percentile(prices, Decimal('0.25'))
        high = _percentile(prices, Decimal('0.75'))
        # Tukey's 1.5 IQR rule flags unusual prices for diagnostics. A valid
        # expensive/cheap itinerary still contributes to all sample statistics.
        margin = Decimal('1.5') * (high - low)
        outliers = sum(price < low - margin or price > high + margin for price in prices)
    durations = list(zip(*(itinerary.durations for itinerary in itineraries)))
    statistics = MarketStatistics(
        input_quote_count=input_count, selected_quote_count=sum(itinerary.listing_count for itinerary in itineraries),
        observed_min=prices[0], observed_max=prices[-1], outlier_count=outliers,
        duration_min_minutes=[min(direction) for direction in durations],
        duration_max_minutes=[max(direction) for direction in durations])
    return MarketReference(low=low, median=_percentile(prices, Decimal('0.5')), high=high,
                           observation_count=len(prices), stop_profile=list(profile), statistics=statistics,
                           currency=terms.currency, price_scope=terms.scope, taxes=terms.taxes, fees=terms.fees)


def _select_market(request: FlightSearch, quotes: Sequence[LiveQuote],
                   model: ValidatedModelEstimate | None) -> tuple[MarketReference | None, bool]:
    groups = _cohorts(request, quotes)
    if not groups:
        return None, False

    # Foreign references may be retained for internal comparison diagnostics;
    # only INR is ever customer-eligible. Prefer the fewest connections on each
    # leg independent of fare. Opposing round-trip tradeoffs require abstention.
    eligible = {key: items for key, items in groups.items() if key[0].currency == 'INR'} or groups
    profiles = [profile for _, profile in eligible]
    preferred = tuple(min(counts) for counts in zip(*profiles))
    candidates = {terms: items for (terms, profile), items in eligible.items() if profile == preferred}
    if not candidates:
        return None, False
    if model is not None and model.stop_profile == list(preferred):
        fare = model.fare
        matching = _MarketTerms(fare.currency, fare.basis, fare.taxes, fare.fees, None)
        if matching in candidates:
            return _summarize(matching, preferred, candidates[matching], len(quotes)), True

    largest = max(map(len, candidates.values()))
    winners = [terms for terms, items in candidates.items() if len(items) == largest]
    if len(winners) != 1:
        return None, False
    terms = winners[0]
    return _summarize(terms, preferred, candidates[terms], len(quotes)), False
