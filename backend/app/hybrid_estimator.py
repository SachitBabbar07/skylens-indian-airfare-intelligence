"""Select one customer fare from a validated model or comparable observed itineraries."""

from collections import defaultdict
from collections.abc import Sequence
from dataclasses import dataclass
from datetime import date
from decimal import Decimal
from typing import Annotated, Literal

from pydantic import Field, field_serializer

from backend.app.flight_fares import (
    DOMESTIC_AIRLINES, IATA, IST, Cabin, Contract, Fare, FlightSearch, Journey, LiveQuote, ValidatedModelEstimate,
)


CoverageStatus = Literal['validated', 'unsupported', 'unavailable']
Treatment = Literal['included', 'excluded', 'unknown']
Scope = Literal['party_total']


class SourceStatus(Contract):
    model: str
    market: str


class EstimateResponse(Contract):
    estimated_low: Decimal | None
    estimated_median: Decimal | None
    estimated_high: Decimal | None
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
    disclaimer: str

    @field_serializer('estimated_low', 'estimated_median', 'estimated_high', when_used='json-unless-none')
    def serialize_amount(self, amount: Decimal) -> str:
        return format(amount, 'f')


class MarketReference(Contract):
    low: Decimal
    median: Decimal
    high: Decimal
    currency: str
    price_scope: Scope
    taxes: Treatment
    fees: Treatment
    observation_count: int


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

    reference, comparable = _select_market(request, quotes, model_value)
    market_eligible = reference is not None and reference.currency == 'INR'
    if market_eligible:
        market_status = 'available'
    elif quotes:
        market_status = 'incompatible_observations'
    elif market_status == 'available':
        market_status = 'no_observations'

    observations = 0
    if model_value is not None:
        method = 'historical_ml'
        low = median = high = model_value.amount
        scope, taxes, fees = model_value.basis, model_value.taxes, model_value.fees
        disclaimer = 'Historical model estimate for the full party. The booking price can change.'
    elif market_eligible:
        method = 'market_reference'
        low, median, high = reference.low, reference.median, reference.high
        scope, taxes, fees = reference.price_scope, reference.taxes, reference.fees
        observations = reference.observation_count
        disclaimer = ('Indicative fare for the full party based on one observed itinerary.'
                      if observations == 1 else
                      'Indicative fare for the full party based on comparable observed itineraries.')
        disclaimer += ' The booking price can change.'
    else:
        method = 'unavailable'
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
        price_scope=scope, taxes=taxes, fees=fees, observation_count=observations, disclaimer=disclaimer)
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


def _itinerary_prices(variants: dict[tuple, set[Decimal]]) -> list[Decimal]:
    # An optional flight number or stop count can be absent in a normalized
    # observation. A partial record can add a price to a unique match, but
    # cannot receive its own weight when several known flights could match.
    identified = {key: prices.copy() for key, prices in variants.items() if None not in key}
    partial_keys = sorted((key for key in variants if None in key), key=lambda key: key.count(None))
    for partial in partial_keys:
        matches = [key for key in identified if all(p is None or p == k for p, k in zip(partial, key))]
        if len(matches) == 1:
            identified[matches[0]].update(variants[partial])
        elif not matches:
            identified[partial] = variants[partial].copy()
    return [_percentile(sorted(prices), Decimal('0.5')) for prices in identified.values()]


def _summarize(terms: _MarketTerms, quotes: list[LiveQuote]) -> MarketReference:
    # Group by every leg, including the inbound schedule. IDs identify offers,
    # and a fare change or duplicate listing does not create another itinerary.
    schedules = defaultdict(lambda: defaultdict(set))
    for quote in quotes:
        schedule = tuple((leg.origin, leg.destination, leg.departure, leg.arrival,
                          tuple(' '.join(name.casefold().split()) for name in leg.airlines))
                         for leg in quote.legs)
        details = tuple(field for leg in quote.legs for field in (tuple(leg.flight_numbers) or None, leg.stops))
        schedules[schedule][details].add(quote.fare.amount)

    prices = sorted(price for variants in schedules.values() for price in _itinerary_prices(variants))
    return MarketReference(low=_percentile(prices, Decimal('0.25')), median=_percentile(prices, Decimal('0.5')),
                           high=_percentile(prices, Decimal('0.75')), observation_count=len(prices),
                           currency=terms.currency, price_scope=terms.scope, taxes=terms.taxes, fees=terms.fees)


def _select_market(request: FlightSearch, quotes: Sequence[LiveQuote],
                   model_value: Fare | None) -> tuple[MarketReference | None, bool]:
    groups = defaultdict(list)
    for quote in quotes:
        if _matches_quote(request, quote):
            fare = quote.fare
            source = quote.source_name if 'unknown' in (fare.taxes, fare.fees) else None
            terms = _MarketTerms(fare.currency, fare.basis, fare.taxes, fare.fees, source)
            groups[terms].append(quote)
    if not groups:
        return None, False
    if model_value is not None:
        matching = _MarketTerms(model_value.currency, model_value.basis, model_value.taxes, model_value.fees, None)
        if matching in groups:
            return _summarize(matching, groups[matching]), True

    # This product serves verified INR totals. A foreign reference can be kept
    # internally for source diagnostics, but is never converted or displayed.
    eligible = {terms: observations for terms, observations in groups.items() if terms.currency == 'INR'}
    candidates = [_summarize(terms, observations) for terms, observations in (eligible or groups).items()]
    largest = max(reference.observation_count for reference in candidates)
    winners = [reference for reference in candidates if reference.observation_count == largest]
    return (winners[0] if len(winners) == 1 else None), False
