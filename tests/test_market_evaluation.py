"""Synthetic software fixtures only. These do not enter a quote store or an accuracy report."""
from copy import deepcopy
from datetime import date, datetime, timedelta, timezone
import json

import pytest

from backend.app.flight_fares import FlightSearch, LiveQuote
from backend.app.hybrid_estimator import select_estimate
from skylens.evaluate_market import evaluate, evaluate_store, load_pairs, metrics
from skylens.quotes import Quote, digest, encoded, resolved_records, temporal_split
from test_quotes import fixture as quote_store_fixture, run


TIME = datetime(2025, 3, 1, 6, tzinfo=timezone.utc)
START = TIME - timedelta(days=1)
PAIRS = {("Synthetic provider", "test-independent")}


def fixture(origin="BLR", destination="COK", hour=10, truth=221):
    day = date(2025, 3, 10)
    request = FlightSearch.model_construct(origin=origin, destination=destination, journey="one_way",
                                           departure_date=day, cabin="economy")
    departure = datetime(2025, 3, 10, hour, tzinfo=timezone.utc)
    arrival = departure + timedelta(hours=1)
    leg = dict(origin=origin, destination=destination, departure=departure, arrival=arrival,
               airlines=["Synthetic carrier"], stops=0, flight_numbers=["ZZ91"], duration_minutes=60)
    offer = LiveQuote(id="software-only", source="live_quote", source_name="Synthetic provider",
                      retrieved_at=TIME, journey="one_way", cabin="economy", travellers=request.travellers,
                      availability="available", legs=[leg], fare=dict(amount="201", currency="INR",
                      basis="party_total", taxes="included", fees="included"))
    response = select_estimate(request, None, [offer], coverage_status="unsupported", market_status="available").response
    capture = dict(captured_at=TIME.isoformat(), computed_at=TIME.isoformat(),
                   request=request.model_dump(mode="json"), quotes=[offer.model_dump(mode="json")],
                   response=response.model_dump(mode="json"))
    label = Quote(quote_id=f"fixture-{origin}-{destination}-{hour}", source_id="test-independent",
                  source_name="Independent software fixture", source_url="https://test.invalid/",
                  source_terms_reference="https://test.invalid/terms", environment="historical",
                  collected_at_utc=TIME + timedelta(minutes=1), origin_airport=origin, destination_airport=destination,
                  departure_date=day, journey_type="one_way", airline="Synthetic carrier", cabin_class="Economy",
                  number_of_passengers=1, passenger_composition={"adults": 1}, currency="INR",
                  displayed_total=truth, total_price_scope="per_passenger", taxes_status="included", fees_status="included",
                  stops=0, availability_status="selectable", itinerary_segments=[dict(
                      origin=origin, destination=destination, departure=departure, arrival=arrival,
                      flight_number="ZZ91", marketing_airline="Synthetic carrier", cabin_class="Economy")])
    return capture, label


def test_independent_forward_matches_have_signed_metrics_and_no_small_sample_coverage():
    a, first = fixture()
    b, second = fixture("COK", "BLR", truth=191)
    result = evaluate([a, b, a], [first, second, first], PAIRS, START)
    overall = result["overall"]
    assert overall["n"] == 2
    assert overall["mae_inr"] == overall["median_absolute_error_inr"] == 15
    assert overall["bias_inr"] == -5
    assert overall["rmse_inr"] == pytest.approx((250)**0.5)
    assert overall["mape_percent"] == pytest.approx((20 / 221 + 10 / 191) * 50)
    assert overall["band_n"] == 0 and overall["band_coverage"] is None
    assert result["route_groups"]["metro_to_regional"]["n"] == 1
    assert result["route_groups"]["regional_to_metro"]["n"] == 1


@pytest.mark.parametrize("field,value", [
    ("currency", "USD"), ("taxes_status", "unknown"), ("fees_status", "excluded"),
    ("number_of_passengers", 2), ("passenger_composition", {"children": 1}),
    ("total_price_scope", "per_segment"), ("cabin_class", "Business"), ("stops", 1),
    ("journey_type", "round_trip"), ("origin_airport", "DEL"), ("airline", "Other"),
    ("source_name", "SYNTHETIC PROVIDER"), ("source_id", "synthetic-provider"),
    ("collected_at_utc", TIME - timedelta(seconds=1)), ("collected_at_utc", TIME + timedelta(hours=1)),
])
def test_different_products_sources_and_times_are_excluded(field, value):
    capture, label = fixture()
    changed = label.model_copy(update={field: value})
    assert evaluate([capture], [changed], PAIRS, START)["overall"]["n"] == 0


def test_unknown_lineage_different_flights_and_reused_segments_do_not_count():
    capture, label = fixture()
    assert evaluate([capture], [label], set(), START)["overall"]["n"] == 0
    for field, value in [("arrival", label.itinerary_segments[0].arrival + timedelta(minutes=2)),
                         ("flight_number", "ZZ92"), ("marketing_airline", "Other")]:
        segment = label.itinerary_segments[0].model_copy(update={field: value})
        changed = label.model_copy(update={"itinerary_segments": [segment]})
        assert evaluate([capture], [changed], PAIRS, START)["overall"]["n"] == 0
    previous = deepcopy(capture)
    for field in ("captured_at", "computed_at"):
        previous[field] = (START - timedelta(days=1)).isoformat()
    previous["quotes"][0]["retrieved_at"] = previous["captured_at"]
    assert evaluate([previous, capture], [label], PAIRS, START)["overall"]["n"] == 0


def test_retroactive_computation_and_conflicting_capture_replays():
    capture, label = fixture()
    replay = dict(capture, computed_at=(TIME + timedelta(minutes=2)).isoformat())
    assert evaluate([replay], [label], PAIRS, START)["overall"]["n"] == 0
    changed = deepcopy(capture)
    changed["response"]["estimated_median"] = "811"
    with pytest.raises(ValueError):
        evaluate([capture, changed], [label], PAIRS, START)


@pytest.mark.parametrize("saved_response", ["identical", "changed", "absent"])
def test_offline_replay_only_preserves_time_for_an_identical_saved_prediction(tmp_path, saved_response):
    from scripts.probe_market_fares import summarize

    capture, _ = fixture()
    expected = deepcopy(capture["response"])
    if saved_response == "changed":
        capture["response"]["estimated_median"] = "811"
    elif saved_response == "absent":
        del capture["response"], capture["computed_at"]
    capture["market_status"] = "available"
    directory = tmp_path / "captures"
    directory.mkdir()
    (directory / "search.json").write_text(json.dumps(capture), encoding="utf-8")
    summarize(directory, tmp_path / "summary.json")
    result = json.loads((directory / "estimates.jsonl").read_text(encoding="utf-8"))
    assert result["response"] == expected
    computed = datetime.fromisoformat(result["computed_at"])
    if saved_response == "identical":
        assert computed == TIME
    else:
        assert computed > TIME


def test_empty_private_store_and_no_capture_never_produce_metrics(tmp_path):
    result = evaluate_store(tmp_path, [], None, set())
    assert result["verified_targets"] == result["overall"]["n"] == 0
    assert result["overall"]["mae_inr"] is None
    assert not list(tmp_path.iterdir())


def test_frozen_intake_evidence_required_for_nonempty_store(quote_store_fixture, tmp_path):
    q, _, _, _, store, _ = quote_store_fixture
    assert run(quote_store_fixture, [q])["verified_targets"] == 1
    with pytest.raises(ValueError, match="frozen"):
        evaluate_store(store, [], None, set())
    records, _ = resolved_records(store)
    start = datetime(2025, 1, 1, tzinfo=timezone.utc)
    frozen = temporal_split(records, [start - timedelta(days=2), start - timedelta(days=1), start])
    frozen["dataset_sha256"] = digest(encoded(records))
    manifest = tmp_path / "split.json"
    manifest.write_text(json.dumps(frozen), encoding="utf-8")
    assert evaluate_store(store, [], manifest, set())["test_targets"] == 1
    frozen["assignments"]["test"].clear()
    manifest.write_text(json.dumps(frozen))
    with pytest.raises(ValueError, match="Frozen split"):
        evaluate_store(store, [], manifest, set())
    (store / "evidence" / (q["evidence_sha256"] + ".bin")).write_bytes(b"changed test fixture")
    with pytest.raises(ValueError, match="evidence"):
        evaluate_store(store, [], manifest, set())


def test_lineage_review_is_bound_to_evidence(tmp_path):
    document = tmp_path / "review.txt"
    document.write_bytes(b"Synthetic unit test for source-lineage review")
    manifest = tmp_path / "pairs.json"
    manifest.write_text(json.dumps([dict(provider="Synthetic provider", independent_source_id="test-independent",
                                         reviewed_by="fixture", evidence_reference="review.txt",
                                         evidence_sha256=digest(document.read_bytes()))]))
    assert load_pairs(manifest) == PAIRS
    document.write_bytes(b"tampered")
    with pytest.raises(ValueError, match="evidence"):
        load_pairs(manifest)


def test_band_fraction_requires_independent_displayed_bands():
    bands = [(201, 220, True)] * 15 + [(201, 190, False)] * 5
    assert metrics(bands[:-1])["band_coverage"] is None
    assert metrics(bands + [(201, 190, None)])["band_coverage"] == 0.75


def test_incompatible_exclusions_recorded_even_without_admitted_targets(tmp_path):
    capture, _ = fixture()
    for record in capture["quotes"]:
        record["fare"]["fees"] = "unknown"
    request = FlightSearch.model_validate(capture["request"], context={"as_of_date": TIME.date()})
    offers = [LiveQuote.model_validate(q) for q in capture["quotes"]]
    capture["response"] = select_estimate(request, None, offers, coverage_status="unsupported",
                                          market_status="available").response.model_dump(mode="json")
    result = evaluate_store(tmp_path, [capture], None, set())
    assert result["skipped"] == {"incompatible_target_terms": 1}
    assert result["route_groups"]["metro_to_regional"]["capture_n"] == 1
