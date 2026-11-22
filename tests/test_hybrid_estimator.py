"""Numerical selector tests using software fixtures, without calls to fare sources."""

from datetime import datetime, time, timedelta, timezone
from decimal import Decimal

import pytest

from backend.app import hybrid_estimator
from backend.app.flight_fares import IST, Fare, FlightLeg, FlightSearch, LiveQuote, Travellers


@pytest.fixture
def search():
    return FlightSearch(origin='DEL', destination='IXC', journey='one_way',
                        departure_date=datetime.now(IST).date() + timedelta(days=10),
                        travellers=Travellers(adults=2))


def fare(amount, *, currency='INR', taxes='included', fees='included'):
    return Fare(amount=Decimal(str(amount)), currency=currency, basis='party_total', taxes=taxes, fees=fees)


def quote(search, amount, *, hour=10, identifier=None, source='Software fixture', **price_terms):
    def leg(origin, destination, day):
        departure = datetime.combine(day, time(hour), tzinfo=IST)
        return FlightLeg(origin=origin, destination=destination, departure=departure,
                         arrival=departure + timedelta(hours=1), airlines=['IndiGo'],
                         flight_numbers=[f'6E{hour}'], stops=0)

    legs = [leg(search.origin, search.destination, search.departure_date)]
    if search.return_date:
        legs.append(leg(search.destination, search.origin, search.return_date))
    return LiveQuote(id=identifier or f'fixture-{hour}-{amount}', source='live_quote', availability='available', source_name=source,
                     retrieved_at=datetime.now(timezone.utc), journey=search.journey,
                     cabin=search.cabin, travellers=search.travellers, legs=legs, fare=fare(amount, **price_terms))


def model(search, amount=7000, *, stop_profile=None, **price_terms):
    return hybrid_estimator.ValidatedModelEstimate(
        id='evaluated-test-model', source='ml_estimate', source_name='Historical model fixture',
        evaluation_reference='test-only grouped holdout', retrieved_at=datetime.now(timezone.utc),
        fare=fare(amount, **price_terms), stop_profile=stop_profile, **search.model_dump())


def select(search, prediction=None, quotes=(), **statuses):
    return hybrid_estimator.select_estimate(
        search, prediction, quotes, coverage_status='validated' if prediction else 'unsupported',
        market_status='available' if quotes else 'not_requested', **statuses)


def test_model_only_is_a_point_prediction_for_the_requested_party(search):
    result = select(search, model(search)).response
    assert result.estimation_method == 'historical_ml'
    assert (result.estimated_low, result.estimated_median, result.estimated_high) == (7000, 7000, 7000)
    assert result.range_kind == 'point' and result.stop_profile is result.market_statistics is None
    assert result.model_dump(mode='json')['estimated_low'] == '7000'
    assert result.observation_count == 0
    assert (result.passenger_count, result.journey_type, result.price_scope) == (2, 'one_way', 'party_total')
    assert (result.currency, result.coverage_status, result.source_status.model) == ('INR', 'validated', 'available')


def test_exponent_notation_in_normalized_prices_becomes_plain_decimal_text(search):
    result = select(search, quotes=[quote(search, '1E+4')]).response.model_dump(mode='json')
    assert result['estimated_low'] is result['estimated_high'] is None
    assert result['estimated_median'] == result['market_statistics']['observed_min'] == '10000'


def test_market_median_weights_each_itinerary_once_even_with_repriced_duplicates(search):
    # Same itinerary offered at 1000 and 3000 contributes 2000. Other distinct
    # schedules contribute 4000, 8000 and 12000, giving a median of 6000.
    observations = [quote(search, amount, identifier=str(i)) for i, amount in enumerate([1000, 1000, 3000])]
    observations[1].legs[0].departure = observations[1].legs[0].departure.astimezone(timezone.utc)
    observations.extend(quote(search, price, hour=hour, identifier=str(hour))
                        for hour, price in [(11, 4000), (12, 8000), (13, 12000)])
    for ordered in (observations, list(reversed(observations))):
        result = select(search, quotes=ordered).response
        assert result.estimation_method == 'market_reference'
        assert (result.estimated_low, result.estimated_median, result.estimated_high) == (None, 6000, None)
        assert result.observation_count == 4
        assert (result.market_statistics.observed_min, result.market_statistics.observed_max) == (2000, 12000)
        assert result.market_statistics.selected_quote_count == result.market_statistics.input_quote_count == 6


@pytest.mark.parametrize('hours', [[9], [9, 10, 11]])
def test_equal_or_single_observations_do_not_invent_a_spread(search, hours):
    observations = [quote(search, '4567.89', hour=h, identifier=str(h), taxes='unknown', fees='unknown')
                    for h in hours]
    result = select(search, quotes=observations).response
    assert result.observation_count == len(hours)
    assert result.estimated_low is result.estimated_high is result.market_statistics.outlier_count is None
    assert result.range_kind == 'limited_sample' and result.estimated_median == Decimal('4567.89')
    assert result.taxes == result.fees == 'unknown'
    assert 'tax' in result.disclaimer.lower() and 'fee' in result.disclaimer.lower()


def test_same_schedule_with_missing_optional_details_cannot_get_double_weight(search):
    precise = quote(search, 4000, identifier='numbered')
    partial = quote(search, 8000, identifier='unnumbered')
    partial.legs[0].flight_numbers = []
    partial.legs[0].stops = None
    separate = quote(search, 12000, hour=11)
    result = select(search, quotes=[partial, precise, separate]).response
    assert (result.observation_count, result.estimated_median) == (2, 9000)


def test_same_schedule_ambiguous_offer_cannot_overweight_two_known_flights(search):
    one = quote(search, 4000, identifier='flight-one')
    two = quote(search, 8000, identifier='flight-two')
    two.legs[0].flight_numbers = ['6E99']
    unknown = quote(search, 12000, identifier='incomplete')
    unknown.legs[0].flight_numbers = []
    unknown.legs[0].stops = None
    for ordered in [[one, two, unknown], [unknown, two, one]]:
        result = select(search, quotes=ordered).response
        assert (result.observation_count, result.estimated_median) == (2, 6000)


def test_compatible_model_and_market_preserved_separately_and_model_selected(search):
    decision = select(search, model(search, 6000, stop_profile=[0]), [quote(search, 4000), quote(search, 5000, hour=11)])
    assert decision.comparable
    assert decision.model_value.amount == decision.response.estimated_median == 6000
    assert decision.market_reference.median == 4500
    assert decision.response.estimation_method == 'historical_ml'


@pytest.mark.parametrize('terms', [
    {'currency': 'USD'}, {'taxes': 'excluded'}, {'fees': 'excluded'}, {'taxes': 'unknown'}, {'fees': 'unknown'},
])
def test_mismatched_monetary_terms_or_unknown_treatment_prevent_comparison(search, terms):
    decision = select(search, model(search, 6000, stop_profile=[0]), [quote(search, 4000, **terms)])
    assert not decision.comparable
    assert decision.response.estimation_method == 'historical_ml'
    assert decision.response.estimated_median == 6000


def test_market_prefers_comparable_known_terms_when_a_validated_model_exists(search):
    quotes = [quote(search, 9000, hour=9, fees='unknown'), quote(search, 12000, hour=12, fees='unknown'),
              quote(search, 5000, hour=10)]
    decision = select(search, model(search, stop_profile=[0]), quotes)
    assert decision.comparable
    assert decision.market_reference.median == 5000
    assert decision.market_reference.observation_count == 1


def test_neither_source_returns_unavailable_with_safe_status_and_null_amounts(search):
    decision = hybrid_estimator.select_estimate(search, None, [], coverage_status='unsupported', market_status='timeout')
    result = decision.response
    assert result.estimation_method == 'unavailable' and result.source_status.market == 'timeout'
    assert result.estimated_low is result.estimated_median is result.estimated_high is result.currency is None
    assert result.observation_count == 0 and not decision.comparable
    assert result.range_kind == 'unavailable' and result.stop_profile is result.market_statistics is None


def test_only_quoted_inr_is_eligible_for_customer_display(search):
    foreign = [quote(search, 120, currency='USD'), quote(search, 180, hour=12, currency='USD')]
    assert select(search, quotes=foreign).response.estimation_method == 'unavailable'
    result = select(search, quotes=foreign + [quote(search, 4500)]).response
    assert (result.currency, result.estimated_median, result.observation_count) == ('INR', 4500, 1)


def test_incompatible_market_cohorts_choose_unique_largest_or_abstain_on_tie(search):
    first = quote(search, 4000, taxes='included')
    second = quote(search, 8000, hour=11, taxes='excluded')
    duplicate = quote(search, 4000, taxes='included', identifier='another-listing')
    assert select(search, quotes=[first, duplicate, second]).response.estimation_method == 'unavailable'
    third = quote(search, 10000, hour=12, taxes='excluded')
    result = select(search, quotes=[first, second, third]).response
    assert (result.estimated_median, result.observation_count, result.taxes) == (9000, 2, 'excluded')


def test_unknown_treatments_are_not_pooled_across_independent_sources(search):
    observations = [quote(search, 4000, taxes='unknown', source='A'),
                    quote(search, 6000, hour=11, taxes='unknown', source='B')]
    assert select(search, quotes=observations).response.estimation_method == 'unavailable'


@pytest.mark.parametrize('edits', [
    {'travellers': Travellers(adults=1)}, {'travellers': Travellers(adults=1, children=1)},
    {'cabin': 'business'}, {'origin': 'BOM'}, {'destination': 'MAA'}, {'airline': 'air_india'},
    {'departure_date': datetime.now(IST).date() + timedelta(days=11)},
    {'journey': 'round_trip', 'return_date': datetime.now(IST).date() + timedelta(days=14)},
])
def test_mismatched_search_context_cannot_supply_an_estimate(search, edits):
    wanted = search.model_copy(update=edits)
    decision = select(wanted, model(search), [quote(search, 8000)])
    assert decision.response.estimation_method == 'unavailable'
    assert not decision.comparable


def test_round_trip_matching_checks_local_return_date_and_entire_inbound_leg(search):
    requested = search.model_copy(update={'journey': 'round_trip', 'return_date': search.departure_date + timedelta(days=2)})
    other_day = requested.model_copy(update={'return_date': requested.return_date + timedelta(days=1)})
    assert select(requested, model(other_day), [quote(other_day, 8000)]).response.estimation_method == 'unavailable'
    one = quote(requested, 6000)
    two = quote(requested, 10000, identifier='different-return')
    two.legs[1].departure += timedelta(hours=1)
    two.legs[1].arrival += timedelta(hours=1)
    decision = select(requested, model(requested, stop_profile=[0, 0]), [one, two])
    assert decision.comparable
    assert decision.market_reference.observation_count == 2 and decision.market_reference.median == 8000


@pytest.mark.parametrize('price_terms', [{'currency': 'USD'}, {'taxes': 'unknown'}, {'fees': 'unknown'}])
def test_unverified_or_incompatible_model_price_definition_falls_back_to_valid_market(search, price_terms):
    decision = select(search, model(search, **price_terms), [quote(search, 8000)])
    assert decision.response.estimation_method == 'market_reference'
    assert decision.response.estimated_median == 8000
    assert decision.response.coverage_status == 'unavailable'
    assert decision.response.source_status.model == 'invalid_response'
    assert decision.model_value is None and not decision.comparable


def test_unsupported_coverage_cannot_authorize_a_customer_model(search):
    decision = hybrid_estimator.select_estimate(search, model(search), [], coverage_status='unsupported',
                                                 market_status='unconfigured')
    assert decision.response.estimation_method == 'unavailable'


@pytest.mark.parametrize('profile', [None, [1]])
def test_model_requires_reviewed_matching_stop_scope_to_compare_with_market(search, profile):
    decision = select(search, model(search, stop_profile=profile), [quote(search, 1000)])
    assert decision.response.estimation_method == 'historical_ml'
    assert decision.market_reference.median == 1000 and not decision.comparable


@pytest.mark.parametrize('profile', [[], [-1], [0, 1], ['0'], [False]])
def test_invalid_reviewed_model_stop_profile_is_rejected(search, profile):
    with pytest.raises(ValueError):
        model(search, stop_profile=profile)


def test_distribution_band_requires_eight_distinct_itineraries_and_preserves_extreme_prices(search):
    observations = [quote(search, amount, hour=hour)
                    for hour, amount in enumerate([100, 200, 300, 400, 500, 600, 700, 1800], start=8)]
    # Duplicate listings do not turn seven schedules into eight.
    small = select(search, quotes=observations[:7] + observations[:3]).response
    assert (small.observation_count, small.range_kind, small.estimated_median) == (7, 'limited_sample', 400)
    assert small.estimated_low is small.estimated_high is small.market_statistics.outlier_count is None
    adequate = select(search, quotes=observations).response
    assert (adequate.range_kind, adequate.observation_count) == ('interquartile', 8)
    assert (adequate.estimated_low, adequate.estimated_median, adequate.estimated_high) == (275, 450, 625)
    stats = adequate.market_statistics
    assert (stats.observed_min, stats.observed_max, stats.outlier_count) == (100, 1800, 1)


@pytest.mark.parametrize(('origin', 'destination', 'fewest', 'shortest_fare'), [
    ('BOM', 'BLR', 0, 12000), ('PAT', 'MAA', 1, 2000), ('HYD', 'GAU', 0, 8000),
])
def test_prefer_fewest_stops_across_eligible_inr_terms_independent_of_price_or_listing_count(
        search, origin, destination, fewest, shortest_fare):
    wanted = search.model_copy(update={'origin': origin, 'destination': destination})
    foreign = quote(wanted, 120, currency='USD')
    shortest = quote(wanted, shortest_fare, taxes='unknown')
    shortest.legs[0].stops = fewest
    connections = [quote(wanted, amount, hour=hour) for hour, amount in [(10, 5000), (11, 7000), (12, 9000)]]
    for offer in connections:
        offer.legs[0].stops = fewest + 1
    result = select(wanted, quotes=[foreign, shortest, *connections]).response
    assert (result.estimated_median, result.observation_count, result.stop_profile) == (shortest_fare, 1, [fewest])
    assert (result.market_statistics.input_quote_count, result.market_statistics.selected_quote_count) == (5, 1)


def test_round_trip_selects_minima_per_direction_and_abstains_on_incomparable_patterns(search):
    wanted = search.model_copy(update={'journey': 'round_trip', 'return_date': search.departure_date + timedelta(days=2)})
    outbound_connection = quote(wanted, 1000)
    outbound_connection.legs[0].stops = 1
    inbound_connections = quote(wanted, 3000)
    inbound_connections.legs[1].stops = 2
    observations = [outbound_connection, inbound_connections, inbound_connections]
    assert select(wanted, quotes=observations).response.estimation_method == 'unavailable'
    direct = quote(wanted, 8000)
    result = select(wanted, quotes=[direct, *observations]).response
    assert (result.estimated_median, result.observation_count, result.stop_profile) == (8000, 1, [0, 0])


def test_missing_stop_evidence_cannot_create_a_profile_or_inflate_known_profiles(search):
    unknown = quote(search, 9000)
    unknown.legs[0].stops = None
    assert select(search, quotes=[unknown]).response.estimation_method == 'unavailable'
    direct = quote(search, 1000)
    connection = quote(search, 5000)
    connection.legs[0].stops = 1
    for ordered in [[unknown, direct, connection], [connection, direct, unknown]]:
        result = select(search, quotes=ordered).response
        assert (result.stop_profile, result.estimated_median, result.market_statistics.selected_quote_count) == ([0], 1000, 1)


def test_price_terms_cannot_resolve_an_ambiguous_flight_identity(search):
    direct = quote(search, 1000)
    connection = quote(search, 5000, taxes='excluded')
    connection.legs[0].stops = 1
    unknown = quote(search, 9000)
    unknown.legs[0].stops = None
    result = select(search, quotes=[direct, connection, unknown]).response
    assert (result.stop_profile, result.estimated_median, result.market_statistics.selected_quote_count) == ([0], 1000, 1)


def test_competing_incomplete_flight_numbers_cannot_supply_prices_to_an_unnumbered_itinerary(search):
    direct = quote(search, 1000)
    direct.legs[0].flight_numbers = []
    incomplete = [quote(search, amount) for amount in [9000, 11000]]
    for index, offer in enumerate(incomplete):
        offer.legs[0].stops = None
        offer.legs[0].flight_numbers = [f'6E{index}']
    result = select(search, quotes=[direct, *incomplete]).response
    assert (result.stop_profile, result.estimated_median, result.market_statistics.selected_quote_count) == ([0], 1000, 1)


def test_complementary_partial_round_trip_numbers_do_not_create_two_artificial_itineraries(search):
    wanted = search.model_copy(update={'journey': 'round_trip', 'return_date': search.departure_date + timedelta(days=1)})
    outbound_number = quote(wanted, 4000)
    outbound_number.legs[1].flight_numbers = []
    inbound_number = quote(wanted, 8000)
    inbound_number.legs[0].flight_numbers = []
    separate = quote(wanted, 10000, hour=11)
    for ordered in [[outbound_number, inbound_number, separate], [separate, inbound_number, outbound_number]]:
        result = select(wanted, quotes=ordered).response
        assert (result.observation_count, result.estimated_median) == (1, 10000)


def test_duration_uses_elapsed_leg_times_and_rejects_contradictory_provider_evidence(search):
    wanted = search.model_copy(update={'journey': 'round_trip', 'return_date': search.departure_date + timedelta(days=2)})
    ordinary, longer, inconsistent = [quote(wanted, price, hour=h) for h, price in [(9, 1000), (10, 3000), (11, 9000)]]
    longer.legs[0].arrival += timedelta(minutes=30, seconds=25)
    longer.legs[0].duration_minutes = 90
    longer.legs[1].arrival += timedelta(minutes=120)
    inconsistent.legs[0].duration_minutes = 300
    result = select(wanted, quotes=[ordinary, longer, inconsistent]).response
    stats = result.market_statistics
    assert (result.observation_count, result.estimated_median) == (2, 2000)
    assert (stats.duration_min_minutes, stats.duration_max_minutes) == ([60, 60], [90, 180])
