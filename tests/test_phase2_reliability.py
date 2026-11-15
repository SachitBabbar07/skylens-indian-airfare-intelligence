"""Regression tests for observed phase-two reliability defects."""
import json
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from backend.app.main import app

pytestmark = pytest.mark.local_data

ROOT = Path(__file__).resolve().parents[1]


@pytest.fixture(scope="module")
def client():
    with TestClient(app, raise_server_exceptions=False) as value:
        yield value


def scenario(profile):
    minute = round(profile["hour_min"] * 60)
    return {
        **{key: profile[key] for key in ["origin", "destination", "airline", "cabin_class", "stops"]},
        "model_id": "cabin_2023",
        "duration_minutes": float(profile["duration_min"]),
        "days_left": int(profile["lead_min"]),
        "departure_hour": minute // 60 + (minute % 60) / 60,
        "research_acknowledged": True,
    }


def test_every_advertised_profile_accepts_clock_minute_conversion(client):
    profiles = client.get("/supported-options").json()["combinations"]
    assert len(profiles) == 592
    for profile in profiles:
        response = client.post("/predict", json=scenario(profile))
        assert response.status_code == 200, (profile, response.text)


def test_actual_clock_precision_regressions(client):
    evidence = json.loads((ROOT / "data/metadata/phase2/clock_precision_probe.json").read_text())
    assert evidence["failures"] == 7
    for example in evidence["failure_examples"]:
        assert client.post("/predict", json=example["inputs"]).status_code == 200


def test_clock_tolerance_does_not_accept_a_minute_outside_support(client):
    profile = client.get("/supported-options").json()["combinations"][0]
    body = scenario(profile)
    body["departure_hour"] = profile["hour_min"] - 1 / 60
    assert client.post("/predict", json=body).status_code == 422


def test_interval_withheld_when_offline_holdout_misses_serving_domain(client):
    profile = client.get("/supported-options").json()["combinations"][0]
    result = client.post("/predict", json=scenario(profile)).json()
    assert result["interval"] is None
    assert result["interval_status"] == "withheld_unvalidated_serving_domain"
    assert result["currency"] is None
    assert result["unit"] == "source fare units"


def test_semantics_are_audited_per_source_and_not_promoted(client):
    result = client.get("/fare-semantics").json()
    assert result["currency"] is None and result["price_scope"] == "unknown"
    assert result["evidence"]["currency_status"] == "undocumented"
    assert result["evidence"]["source"] == "yashdharme36/airfare-ml-predicting-flight-fares"
    assert result["evidence"]["production_eligible"] is False


def test_directory_distinguishes_master_observed_and_model_support(client):
    rows = client.get("/airports", params={"supported_only": False}).json()["airports"]
    by_code = {row["iata_code"]: row for row in rows if row["iata_code"]}
    assert by_code["DEL"]["serving_status"] == "eligible_research_profile"
    assert by_code["PNQ"]["serving_status"] == "fare_evidence_other_cohort"
    assert any(row["serving_status"] == "no_iata_code" for row in rows)
    network = client.get("/airports", params={
        "model_id": "network_2020", "supported_only": False, "query": "DEL"
    }).json()["airports"]
    assert next(row for row in network if row["iata_code"] == "DEL")["serving_status"] == "insufficient_profile_support"


def test_training_data_and_model_binaries_still_match_checkpoint():
    import hashlib
    checkpoint = json.loads((ROOT / "data/metadata/phase2_checkpoint.json").read_text())
    checkpoint_dir = ROOT / "backups" / Path(checkpoint["checkpoint_dir"]).name
    files = json.loads((checkpoint_dir / "baseline_manifest.json").read_text())["files"]
    for name, info in files.items():
        if name.startswith(("data/raw/", "data/processed/", "data/interim/", "models/")):
            assert hashlib.sha256((ROOT / name).read_bytes()).hexdigest() == info["sha256"], name


def test_audit_sources_cannot_enter_frozen_training_manifest():
    registry = json.loads((ROOT / "data/metadata/dataset_registry.json").read_text())
    audits = [entry for entry in registry if entry.get("role") == "audit_only_not_training"]
    assert len(audits) == 4
    manifest = json.loads((ROOT / "config/sources.json").read_text())["fare_sources"]
    assert all(entry["source"] not in manifest and entry["training_eligible"] is False
               for entry in audits)
