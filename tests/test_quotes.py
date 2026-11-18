"""SYNTHETIC SOFTWARE FIXTURES ONLY. Never fare evidence or ML training data.

All permissions and amounts below are invented inside temporary directories to
exercise validation. No real airline/source permission is represented.
"""
import csv
import json
from copy import deepcopy
from datetime import datetime, timezone
from pathlib import Path

import pytest
from pydantic import ValidationError

from skylens.quotes import (Quote, REQUIRED_EVIDENCE, digest, encoded, intake,
                            local_file, resolved_records, summary, temporal_split)

UTC = timezone.utc
CODES = {"DEL", "BOM", "PNQ"}


@pytest.fixture
def fixture(tmp_path, monkeypatch):
    monkeypatch.setattr("skylens.quotes.utc_now", lambda: datetime(2026, 1, 1, tzinfo=UTC))
    evidence = tmp_path / "evidence"
    evidence.mkdir()
    permission = b"SYNTHETIC TEST PERMISSION. Grants no real-world rights."
    quote_evidence = b"SYNTHETIC QUOTE TEST. Invented software fixture, not a real airfare."
    (evidence / "permission.txt").write_bytes(permission)
    (evidence / "quote.txt").write_bytes(quote_evidence)
    grant = {"source_id": "synthetic-test", "hosts": ["quotes.example.invalid"], "methods": ["manual"],
             "collection_allowed": True, "storage_allowed": True, "ml_use_allowed": True,
             "no_cost_confirmed": True, "valid_from": "2025-01-01T00:00:00Z",
             "valid_until": "2030-01-01T00:00:00Z", "retention_until": "2031-01-01T00:00:00Z",
             "daily_observation_limit": 100, "terms_url": "https://quotes.example.invalid/terms",
             "reviewed_by": "synthetic-test-reviewer", "reviewed_at_utc": "2025-01-01T00:00:00Z",
             "permission_reference": "permission.txt", "permission_sha256": digest(permission)}
    permissions = tmp_path / "permissions.json"
    permissions.write_text(json.dumps({"sources": [grant]}), encoding="utf-8")
    q = {"quote_id": "synthetic-1", "source_id": "synthetic-test", "source_name": "SYNTHETIC SOFTWARE TEST",
         "source_url": "https://quotes.example.invalid/", "source_terms_reference": grant["terms_url"],
         "environment": "historical", "acquisition_method": "manual", "collected_at_utc": "2025-01-02T00:00:00Z",
         "origin_airport": "DEL", "destination_airport": "BOM", "departure_date": "2025-02-01",
         "journey_type": "one_way", "airline": "Synthetic Test Carrier", "cabin_class": "Economy",
         "number_of_passengers": 1, "passenger_composition": {"adults": 1}, "currency": "INR",
         "displayed_total": "100.00", "base_fare": "80.00", "taxes": "15.00", "fees": "5.00",
         "total_price_scope": "complete_booking", "taxes_status": "included", "fees_status": "included",
         "availability_status": "selectable", "stops": 0, "duration_minutes": 120,
         "itinerary_segments": [{"origin": "DEL", "destination": "BOM", "departure": "2025-02-01T10:00:00+05:30",
                                  "arrival": "2025-02-01T12:00:00+05:30", "marketing_airline": "Synthetic Test Carrier",
                                  "flight_number": "TEST001", "cabin_class": "Economy", "leg": "outbound"}],
         "evidence_reference": "quote.txt", "evidence_sha256": digest(quote_evidence),
         "reviewed_by": "synthetic-test-reviewer", "reviewed_at_utc": "2025-01-20T00:00:00Z",
         "semantic_evidence": {k: "synthetic fixture line" for k in REQUIRED_EVIDENCE}}

    def save(rows, name="input.csv"):
        path = tmp_path / name
        with path.open("w", encoding="utf-8", newline="") as out:
            writer = csv.DictWriter(out, fieldnames=list(Quote.model_fields))
            writer.writeheader()
            for row in rows:
                writer.writerow({k: json.dumps(v) if isinstance(v, (dict, list)) else v for k, v in row.items()})
        return path

    return q, grant, permissions, evidence, tmp_path / "store", save


def run(fixture, rows, commit=True, name="input.csv"):
    q, grant, permissions, evidence, store, save = fixture
    return intake(save(rows, name), permissions, evidence, store, CODES, commit)


def test_header_only_template_has_zero_observations(fixture):
    result = run(fixture, [])
    assert result["rows"] == summary(fixture[4])["verified_targets"] == 0


def test_candidate_uses_frozen_holdout_and_never_writes_for_empty_or_changed_data(fixture):
    pytest.importorskip("catboost")
    from datetime import timedelta
    from skylens.train_verified_fare import train_candidate

    store = fixture[4]
    manifest = store / "split.json"
    output = store / "experiment"
    cuts = [datetime(2025, m, 1, tzinfo=UTC) for m in (2, 3, 4)]

    def freeze():
        rows, _ = resolved_records(store)
        frozen = temporal_split(rows, cuts)
        frozen["dataset_sha256"] = digest(encoded(rows))
        manifest.parent.mkdir(parents=True, exist_ok=True)
        manifest.write_bytes(encoded(frozen))

    freeze()
    with pytest.raises(ValueError, match="No verified fare observations"):
        train_candidate(store, manifest, output)
    assert not output.exists()

    rows = []
    for month in range(1, 5):
        collected = datetime(2025, month, 2, tzinfo=UTC)
        for lead in (5, 10, 15):
            quote = deepcopy(fixture[0])
            departure = (collected + timedelta(days=lead)).date()
            quote.update(quote_id=f"software-test-{month}-{lead}", collected_at_utc=collected.isoformat(),
                         departure_date=departure.isoformat(), displayed_total=str(100 + lead),
                         base_fare=str(80 + lead), reviewed_at_utc="2025-05-01T00:00:00Z")
            quote["itinerary_segments"][0].update(departure=f"{departure}T10:00:00+05:30",
                                                  arrival=f"{departure}T12:00:00+05:30")
            rows.append(quote)
    assert run(fixture, rows)["verified_targets"] == 12
    with pytest.raises(ValueError, match="Frozen split does not match"):
        train_candidate(store, manifest, output)
    assert not output.exists()
    freeze()
    result = train_candidate(store, manifest, output)
    assert result["partitions"]["test"]["observations"] == 3
    assert result["partitions"]["test"]["baseline_mae_inr"] == pytest.approx(10 / 3)
    assert result["partitions"]["test"]["mae_inr"] >= 0
    profile, = result["test_profiles"]
    assert (profile["origin"], profile["destination"], profile["within_training_support"]) == ("DEL", "BOM", 3)
    assert result["serving_approved"] is False
    assert digest((output / "model.cbm").read_bytes()) == result["model_sha256"]
    assert json.loads((output / "evaluation.json").read_text()) == result


def test_phase5_license_label_does_not_override_missing_ml_permission(fixture):
    q, grant, permissions, _, _, _ = fixture
    q.update(license_name='CC0', license_url='https://creativecommons.org/publicdomain/zero/1.0/',
             reuse_status='open_license')
    grant['ml_use_allowed'] = False
    permissions.write_text(json.dumps({'sources': [grant]}))
    assert run(fixture, [q])['research_only'] == 1
    assert summary(fixture[4])['verified_targets'] == 0


def test_phase5_optional_lead_time_stays_unknown_or_matches_actual_dates(fixture):
    from skylens.quotes import Quote, IST
    q = fixture[0]
    parsed = Quote.model_validate(q)
    assert parsed.booking_lead_days is None and parsed.license_name is None
    lead = (parsed.departure_date-parsed.collected_at_utc.astimezone(IST).date()).days
    q['booking_lead_days'] = lead+1
    assert run(fixture, [q])['quarantined'] == 1


def test_authenticity_is_human_review_and_intake_never_trains(fixture):
    q = fixture[0]
    assert run(fixture, [q])["verified_targets"] == 1
    s = summary(fixture[4])
    assert s["verified_targets"] == s["unique_itineraries"] == s["collection_days_ist"] == 1
    assert not s["training_automatically_enabled"]
    assert not list(fixture[4].rglob("*.cbm"))


@pytest.mark.parametrize("field,value", [("currency", None), ("currency", "USD"), ("taxes_status", "unknown"),
    ("fees_status", "excluded"), ("total_price_scope", "unknown"), ("availability_status", "indicative"),
    ("environment", "test"), ("reviewed_by", None), ("semantic_evidence", {}),
    ("evidence_sha256", "0" * 64), ("evidence_reference", "missing.txt"), ("itinerary_segments", [])])
def test_unknowns_never_enter_verified_target(fixture, field, value):
    q = deepcopy(fixture[0]); q[field] = value
    assert run(fixture, [q])["research_only"] == 1
    assert summary(fixture[4])["verified_targets"] == 0


@pytest.mark.parametrize("field", ["collection_allowed", "storage_allowed", "no_cost_confirmed"])
def test_denied_sources_are_not_even_archived(fixture, field):
    q, grant, permissions, _, store, _ = fixture
    grant[field] = False
    permissions.write_text(json.dumps({"sources": [grant]}))
    with pytest.raises(PermissionError):
        run(fixture, [q])
    assert not store.exists()


def test_ml_denied_can_be_retained_only_as_research(fixture):
    q, grant, permissions, _, store, _ = fixture
    grant["ml_use_allowed"] = False
    permissions.write_text(json.dumps({"sources": [grant]}))
    assert run(fixture, [q])["research_only"] == 1
    assert summary(store)["verified_targets"] == 0


def test_permission_hash_and_collection_window_are_enforced(fixture):
    q, grant, permissions, evidence, store, _ = fixture
    (evidence / "permission.txt").write_text("modified synthetic permission")
    with pytest.raises(ValueError, match="checksum"):
        run(fixture, [q])
    assert not store.exists()


def test_authorized_window_and_source_domain_cannot_be_bypassed(fixture):
    q = deepcopy(fixture[0]); q["collected_at_utc"] = "2024-12-31T00:00:00Z"
    with pytest.raises(PermissionError, match="period"):
        run(fixture, [q])
    q = deepcopy(fixture[0]); q["source_url"] = "https://other.example.invalid/"
    with pytest.raises(PermissionError, match="outside permission"):
        run(fixture, [q])
    assert not fixture[4].exists()


def test_quote_and_permission_evidence_integrity_and_retention(fixture, monkeypatch):
    run(fixture, [fixture[0]])
    monkeypatch.setattr("skylens.quotes.utc_now", lambda: datetime(2032, 1, 1, tzinfo=UTC))
    assert summary(fixture[4])["verified_targets"] == 0
    monkeypatch.setattr("skylens.quotes.utc_now", lambda: datetime(2026, 1, 1, tzinfo=UTC))
    blob = fixture[4] / "evidence" / (fixture[0]["evidence_sha256"] + ".bin")
    blob.write_text("tampered synthetic evidence")
    assert summary(fixture[4])["verified_targets"] == 0


def test_unknown_and_duplicate_headers_are_rejected(fixture):
    q, _, permissions, evidence, store, save = fixture
    path = save([q]); text = path.read_text(encoding="utf-8")
    path.write_text(text.replace("quote_id,", "extra,quote_id,", 1), encoding="utf-8")
    with pytest.raises(ValueError, match="headers"):
        intake(path, permissions, evidence, store, CODES)
    assert not store.exists()


def test_no_fabricated_one_way_return_or_divided_passenger_total(fixture):
    q = deepcopy(fixture[0]); q.update(journey_type="round_trip", return_date="2025-02-05")
    assert run(fixture, [q])["quarantined"] == 1  # outbound alone cannot prove a return
    q = deepcopy(fixture[0]); q.update(number_of_passengers=2, passenger_composition={"adults": 2}, price_per_passenger="50")
    with pytest.raises(ValidationError):
        Quote.model_validate(q)


def test_round_trip_requires_actual_connected_segments_and_evidence(fixture):
    q = deepcopy(fixture[0]); q.update(journey_type="round_trip", return_date="2025-02-05", duration_minutes=None)
    s = deepcopy(q["itinerary_segments"][0]); s.update(origin="BOM", destination="DEL", departure="2025-02-05T12:00:00+05:30",
                     arrival="2025-02-05T14:00:00+05:30", leg="inbound", flight_number="TEST002")
    q["itinerary_segments"].append(s)
    q["semantic_evidence"]["return_date"] = "synthetic fixture return line"
    assert run(fixture, [q])["verified_targets"] == 1
    assert summary(fixture[4])["genuine_round_trip_targets"] == 1  # synthetic assertion exercises code only


@pytest.mark.parametrize("change", [
    {"collected_at_utc": "2025-01-02T00:00:00"}, {"collected_at_local": "2025-01-02T06:30:00+05:30"},
    {"displayed_total": "NaN"}, {"displayed_total": "-1"}, {"taxes": "19"},
    {"passenger_composition": {"adults": True}}, {"return_date": "2025-02-05"},
    {"source_url": "https://quotes.example.invalid/?token=private"}, {"unexpected": "field"}])
def test_malformed_semantics_fail_schema(fixture, change):
    q = deepcopy(fixture[0]); q.update(change)
    with pytest.raises(ValidationError):
        Quote.model_validate(q)


def test_exact_replay_duplicate_ids_and_repeated_snapshots(fixture):
    q = fixture[0]
    run(fixture, [q])
    assert run(fixture, [q])["replayed"]
    q2 = deepcopy(q); q2["quote_id"] = "synthetic-copy"
    run(fixture, [q2], name="copy.csv")
    q3 = deepcopy(q); q3.update(quote_id="synthetic-refresh", collected_at_utc="2025-01-02T01:00:00Z")
    run(fixture, [q3], name="refresh.csv")
    q4 = deepcopy(q); q4.update(quote_id="synthetic-next-day", collected_at_utc="2025-01-03T00:00:00Z")
    run(fixture, [q4], name="next.csv")
    s = summary(fixture[4])
    assert s["raw_rows"] == 4 and s["duplicate_snapshots"] == 1
    assert s["verified_targets"] == 3 and s["unique_itineraries"] == 1
    assert s["collection_days_ist"] == s["itinerary_days"] == 2


def test_interrupted_receipt_write_is_recoverable_without_double_quota(fixture):
    q, grant, permissions, _, store, _ = fixture
    grant["daily_observation_limit"] = 1
    permissions.write_text(json.dumps({"sources": [grant]}))
    run(fixture, [q])
    next((store / "receipts").glob("*.json")).unlink()
    assert run(fixture, [q])["replayed"]
    assert summary(store)["raw_rows"] == 1


def test_malformed_reuse_of_quote_id_blocks_previous_target(fixture):
    q = fixture[0]; run(fixture, [q])
    invalid = deepcopy(q); invalid["displayed_total"] = "-1"
    assert run(fixture, [invalid], name="bad.csv")["quarantined"] == 1
    s = summary(fixture[4])
    assert s["verified_targets"] == 0 and s["conflicted_rows_excluded"] == 1


def test_conflict_excludes_both_versions_and_preserves_raw(fixture):
    q = fixture[0]; run(fixture, [q])
    altered = deepcopy(q); altered.update(displayed_total="101", base_fare="81")
    run(fixture, [altered], name="conflict.csv")
    assert summary(fixture[4])["conflicted_rows_excluded"] == 2
    assert summary(fixture[4])["verified_targets"] == 0
    assert len(list((fixture[4] / "raw").glob("*.csv"))) == 2


def test_same_snapshot_different_id_conflicts(fixture):
    q = fixture[0]; run(fixture, [q])
    altered = deepcopy(q); altered.update(quote_id="synthetic-other-id", displayed_total="101", base_fare="81")
    run(fixture, [altered], name="conflict.csv")
    assert summary(fixture[4])["verified_targets"] == 0


def test_validation_is_read_only_and_raw_modification_is_detected(fixture):
    q = fixture[0]; run(fixture, [q], commit=False)
    assert not fixture[4].exists()
    run(fixture, [q])
    next((fixture[4] / "raw").glob("*.csv")).write_text("tampered")
    with pytest.raises(ValueError, match="modified"):
        summary(fixture[4])


def test_evidence_cannot_escape_directory(fixture):
    with pytest.raises(ValueError):
        local_file(fixture[3], "../permissions.json")


def test_quota_and_unknown_source_abort_without_raw_archive(fixture):
    q, grant, permissions, _, store, _ = fixture
    grant["daily_observation_limit"] = 1
    permissions.write_text(json.dumps({"sources": [grant]}))
    other = deepcopy(q); other["quote_id"] = "synthetic-2"
    with pytest.raises(PermissionError, match="limit"):
        run(fixture, [q, other])
    assert not store.exists()
    q = deepcopy(q); q["source_id"] = "unapproved"
    with pytest.raises(PermissionError):
        run(fixture, [q])


def test_shared_leg_codeshare_cabin_and_return_components_cannot_leak(fixture):
    q = fixture[0]
    rows = []
    for i, day in enumerate([2, 5, 9, 13]):
        v = deepcopy(q); v.update(quote_id=f"synthetic-{i}", collected_at_utc=f"2025-01-{day:02}T00:00:00Z")
        if i % 2:
            v["cabin_class"] = "Business"
            v["itinerary_segments"][0].update(cabin_class="Business", flight_number="CODESHARE")
        rows.append(v)
    run(fixture, rows)
    records, _ = resolved_records(fixture[4])
    cuts = [datetime(2025, 1, d, tzinfo=UTC) for d in [4, 8, 12]]
    split = temporal_split(records, cuts)
    assert len(split["assignments"]["purged_cross_boundary"]) == 4
    assert not split["ready_for_experiment_review"]
    assert not split["assignments"]["test"]


def test_independent_itineraries_split_chronologically(fixture):
    q = fixture[0]; rows = []
    for i, day in enumerate([2, 5, 9, 13]):
        v = deepcopy(q); v.update(quote_id=f"synthetic-{i}", collected_at_utc=f"2025-01-{day:02}T00:00:00Z",
                                  departure_date=f"2025-02-{i + 1:02}")
        v["itinerary_segments"][0].update(departure=f"2025-02-{i + 1:02}T10:00:00+05:30",
                                          arrival=f"2025-02-{i + 1:02}T12:00:00+05:30")
        rows.append(v)
    run(fixture, rows)
    records, _ = resolved_records(fixture[4])
    split = temporal_split(records, [datetime(2025, 1, d, tzinfo=UTC) for d in [4, 8, 12]])
    assert all(len(split["assignments"][k]) == 1 for k in ["train", "validation", "calibration", "test"])
    assert split["ready_for_experiment_review"]  # structural only; 4 synthetic records do not validate any model
