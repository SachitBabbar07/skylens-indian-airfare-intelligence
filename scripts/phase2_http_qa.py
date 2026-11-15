"""Permitted HTTP/API checks. This is explicitly not browser QA."""
import argparse
import json
import math
import re
from pathlib import Path
import httpx

ROOT = Path(__file__).resolve().parents[1]


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--base-url", default="http://127.0.0.1:8000")
    parser.add_argument("--output", type=Path, default=ROOT / "reports/phase2_http_integration.json")
    args = parser.parse_args()
    failures, expected_errors = [], []
    prediction_checks = explanation_checks = 0
    with httpx.Client(base_url=args.base_url, timeout=30) as client:
        health = client.get("/health")
        health.raise_for_status()
        page = client.get("/")
        page.raise_for_status()
        assets = re.findall(r'(?:src|href)="([^"]+\.(?:js|css|svg))"', page.text)
        for asset in assets:
            response = client.get(asset)
            if response.status_code != 200:
                failures.append({"asset": asset, "status": response.status_code})
        profiles = client.get("/supported-options").json()["combinations"]
        for profile in profiles:
            body = {key: profile[key] for key in
                    ["origin", "destination", "airline", "cabin_class", "stops"]}
            body.update(model_id="cabin_2023", days_left=int(profile["lead_min"]),
                        duration_minutes=float(profile["duration_min"]), research_acknowledged=True)
            variants = [
                float(profile["hour_min"]),
                (round(profile["hour_min"] * 60) // 60 +
                 round(profile["hour_min"] * 60) % 60 / 60),
                (round(profile["hour_max"] * 60) // 60 +
                 round(profile["hour_max"] * 60) % 60 / 60),
            ]
            for index, hour in enumerate(variants):
                body["departure_hour"] = hour
                response = client.post("/research/predict", json=body)
                prediction_checks += 1
                if response.status_code != 200:
                    failures.append({"profile": body, "variant": index, "status": response.status_code})
                    continue
                result = response.json()
                assert result["currency"] is None and result["unit"] == "source fare units"
                assert result["interval"] is None
                assert result["interval_status"] == "withheld_unvalidated_serving_domain"
                if index == 0:
                    explanation = client.post("/research/explain", json=body)
                    explanation_checks += 1
                    if explanation.status_code != 200:
                        failures.append({"explain": body, "status": explanation.status_code})
                    else:
                        data = explanation.json()
                        assert math.isclose(data["estimate"], result["estimate"], abs_tol=1e-7)
                        assert abs(data["baseline"] + sum(
                            value["contribution"] for value in data["contributions"]
                        ) - result["estimate"]) < 1e-6
        valid = {
            **{key: profiles[0][key] for key in ["origin", "destination", "airline", "cabin_class", "stops"]},
            "model_id": "cabin_2023", "days_left": int(profiles[0]["lead_min"]),
            "duration_minutes": float(profiles[0]["duration_min"]),
            "departure_hour": float(profiles[0]["hour_min"]), "research_acknowledged": True,
        }
        invalid = [
            {"origin": "ZZZ"}, {"origin": "PNQ"}, {"destination": valid["origin"]},
            {"airline": "unknown"}, {"cabin_class": "First"}, {"journey_type": "round_trip"},
            {"journey_type": "multi_city"}, {"duration_minutes": 0}, {"days_left": -1},
            {"days_left": 1.5}, {"return_date": "2026-01-01"}, {"passenger_count": 2},
            {"stops": 7}, {"research_acknowledged": False}, {"model_id": "network_2020"},
        ]
        for changed in invalid:
            response = client.post("/research/predict", json={**valid, **changed})
            expected_errors.append({"changed_fields": changed, "status": response.status_code})
            if response.status_code != 422:
                failures.append(expected_errors[-1])
        for endpoint in ["/model-info", "/coverage", "/airports", "/airlines",
                         "/route-coverage", "/feature-importance", "/fare-semantics"]:
            assert client.get(endpoint).status_code == 200, endpoint
        airports = client.get("/airports", params={"supported_only": False}).json()
        assert airports["total"] == 661
        assert sum(row["research_eligible"] for row in airports["airports"]) == 7
        assert client.get("/supported-options", params={
            "model_id": "network_2020"}).json()["combinations"] == []
    result = {
        "launch_workflow": "existing run.ps1",
        "profiles": len(profiles), "prediction_requests": prediction_checks,
        "explanation_requests": explanation_checks, "expected_invalid_requests": expected_errors,
        "compiled_assets_checked": assets, "health": health.json(),
        "unexpected_failures": failures,
        "browser_qa": "not performed: saved permission setting denies localhost browser access",
        "currency_display_source_check": "Explicit research diagnostics label unverified model-output units; API currency null. Customer fare prediction is disabled.",
        "browser_console_and_mobile_layout": "unverified",
    }
    args.output.write_text(
        json.dumps(result, indent=2), encoding="utf-8")
    print(json.dumps({key: value for key, value in result.items()
                      if key not in ["expected_invalid_requests", "compiled_assets_checked"]}, indent=2))
    assert not failures


if __name__ == "__main__":
    main()
