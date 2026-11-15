"""Portable request contract and repository checks; no fitted model or fare data."""
from pathlib import Path

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient
from pydantic import ValidationError

from backend.app.schemas import PredictionRequest
from scripts.repository_guard import inspect


def request():
    return {"model_id": "cabin_2023", "origin": "DEL", "destination": "BOM", "airline": "Synthetic Software Test",
            "cabin_class": "Economy", "days_left": 3, "duration_minutes": 120, "stops": 0,
            "departure_hour": 10, "research_acknowledged": True}


@pytest.mark.parametrize("changed", [{"journey_type": "round_trip"}, {"research_acknowledged": False},
    {"currency": "INR"}, {"return_date": "2030-01-01"}, {"origin": "BOM"}, {"days_left": 1.5},
    {"duration_minutes": float("inf")}, {"departure_hour": 24}])
def test_current_request_semantics_are_preserved(changed):
    with pytest.raises(ValidationError):
        PredictionRequest.model_validate({**request(), **changed})


def test_fastapi_contract_rejects_bad_input_over_http():
    # Isolated contract transport, explicitly not a mock prediction or native-model QA.
    api = FastAPI()

    @api.post("/validate")
    def validate(body: PredictionRequest):
        return {"journey_type": body.journey_type}

    with TestClient(api) as client:
        assert client.post("/validate", json=request()).status_code == 200
        assert client.post("/validate", json={**request(), "journey_type": "round_trip"}).status_code == 422


def test_scanner_rejects_secret_and_large_private_payload():
    # Compose the fake token at runtime so no token-shaped value enters Git.
    fake = ("gh" + "p_" + "A" * 36).encode()
    assert "GitHub token" in inspect("example.py", fake)
    assert "forbidden payload" in inspect(".env", b"")
    assert "private or regenerable payload" in inspect("data/quotes/example.csv", b"")
    assert "blob exceeds 5 MiB" in inspect("large.txt", b"a" * (5 * 1024 * 1024 + 1))
    assert not inspect(".env.example", b"SKYLENS_CORS_ORIGINS=\n")


def test_training_reads_only_frozen_historical_cohorts():
    root = Path(__file__).resolve().parents[1]
    training = (root / "src/skylens/train.py").read_text(encoding="utf-8")
    assert "skylens.quotes" not in training and "data/quotes" not in training
    assert 'network_2020' in training and 'cabin_2023' in training
