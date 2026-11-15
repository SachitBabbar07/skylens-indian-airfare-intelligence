"""Recompute phase-two evidence without changing a model or training observation."""
from pathlib import Path
import hashlib
import json
import sys

import numpy as np
import pandas as pd
from catboost import CatBoostRegressor

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
from skylens.features import FEATURES, feature_frame
from skylens.train import metrics

OUT = ROOT / "data/metadata/phase2"
REPORTS = ROOT / "reports"
COHORTS = ["cabin_2023", "network_2020", "network_external_2020"]
KEYS = ["origin", "destination", "airline", "cabin_class", "stops"]


def dump(path, value):
    path.write_text(json.dumps(value, indent=2, default=str), encoding="utf-8")


def load_cohort(name):
    data = pd.read_parquet(ROOT / f"data/processed/{name}.parquet")
    if name != "network_external_2020":
        split = pd.read_parquet(ROOT / f"data/processed/{name}_splits.parquet")
        data = data.merge(split[["fingerprint", "split"]], on="fingerprint",
                          validate="one_to_one")
    else:
        data["split"] = "external_challenge"
    data["cohort"] = name
    return data


def main():
    checkpoint = json.loads((ROOT / "data/metadata/phase2_checkpoint.json").read_text())
    checkpoint_dir = ROOT / "backups" / Path(checkpoint["checkpoint_dir"]).name
    baseline = json.loads((checkpoint_dir / "baseline_manifest.json").read_text())
    immutable = {}
    for name, record in baseline["files"].items():
        if name.startswith(("data/raw/", "data/processed/", "data/interim/", "models/")):
            immutable[name] = hashlib.sha256((ROOT / name).read_bytes()).hexdigest() == record["sha256"]
    assert all(immutable.values()), "Original data/model changes require explicit investigation."
    evaluation, domain = {}, {}
    for name in COHORTS[:2]:
        meta = json.loads((ROOT / f"models/{name}/metadata.json").read_text())
        saved = pd.read_parquet(REPORTS / f"{name}_test_predictions.parquet")
        recomputed = metrics(saved.price, saved.prediction)
        for key, value in recomputed.items():
            assert np.isclose(value, meta["test_metrics"][key], atol=1e-8)
        model = CatBoostRegressor()
        model.load_model(str(ROOT / f"models/{name}/model.cbm"))
        sample = saved.sample(min(100, len(saved)), random_state=42)
        assert np.allclose(model.predict(feature_frame(sample)), sample.prediction, atol=1e-7)
        data = load_cohort(name)
        disjoint = {}
        labels = ["train", "validation", "calibration", "test"]
        for i, left in enumerate(labels):
            for right in labels[i + 1:]:
                disjoint[f"{left}/{right}"] = all(
                    set(data[data.split.eq(left)][column]).isdisjoint(
                        data[data.split.eq(right)][column])
                    for column in ["fingerprint", "quote_group"])
        assert all(disjoint.values())
        support = pd.read_csv(ROOT / f"models/{name}/support.csv")
        eligible = support[support.eligible]
        fit = data[data.split.isin(["train", "validation"])]
        test = data[data.split.eq("test")].merge(eligible, on=KEYS, how="left")
        mask = test["n"].notna()
        for column, low, high in [
            ("days_left", "lead_min", "lead_max"),
            ("duration_minutes", "duration_min", "duration_max"),
            ("departure_hour", "hour_min", "hour_max"),
        ]:
            mask &= test[column].between(test[low], test[high])
        domain[name] = {
            "fitting_lead_range": [int(fit.days_left.min()), int(fit.days_left.max())],
            "calibration_lead_range": [
                int(data[data.split.eq("calibration")].days_left.min()),
                int(data[data.split.eq("calibration")].days_left.max())],
            "test_lead_range": [
                int(data[data.split.eq("test")].days_left.min()),
                int(data[data.split.eq("test")].days_left.max())],
            "test_rows": len(test),
            "test_rows_inside_current_serving_domain": int(mask.sum()),
            "eligible_cells": len(eligible),
            "largest_fitting_profile": int(support["n"].max()),
        }
        evaluation[name] = {"recomputed_metrics": recomputed,
                            "native_prediction_sample_matches": True,
                            "split_disjointness": disjoint,
                            "processed_hash_matches_lineage": hashlib.sha256(
                                (ROOT / f"data/processed/{name}.parquet").read_bytes()
                            ).hexdigest() == meta["processed_sha256"]}
    frames = {name: load_cohort(name) for name in COHORTS}
    all_data = pd.concat(frames.values(), ignore_index=True)
    supports = {name: pd.read_csv(ROOT / f"models/{name}/support.csv") for name in COHORTS[:2]}
    codes = sorted(set(all_data.origin) | set(all_data.destination))
    airports = pd.read_csv(REPORTS / "india_airport_master.csv").set_index("iata_code")
    records = []
    for code in codes:
        subset = all_data[all_data.origin.eq(code) | all_data.destination.eq(code)]
        item = {
            "iata_code": code, "airport_name": airports.loc[code, "name"],
            "observations": len(subset),
            "origin_observations": int(subset.origin.eq(code).sum()),
            "destination_observations": int(subset.destination.eq(code).sum()),
            "directional_routes": subset.route.nunique(),
            "airline_labels": "|".join(sorted(subset.airline.unique())),
            "airline_label_count": subset.airline.nunique(),
            "individual_operator_label_count": len(set(
                carrier for label in subset.airline for carrier in label.split("|"))),
            "cabin_labels": "|".join(sorted(subset.cabin_class.unique())),
            "booking_journey_type": "unknown; single-direction records only",
            "currency_verification": "unknown",
            "price_definition": "source-recorded fare; scope unverified",
            "travel_start": str(subset.travel_date.min().date()),
            "travel_end": str(subset.travel_date.max().date()),
            "collection_days": subset.collection_date.nunique(),
            "quote_groups": subset.quote_group.nunique(),
            "independence": "not established; quotes/flight services share collection days",
            "core_feature_missing_percent": float(
                subset[FEATURES + ["price", "travel_date", "collection_date"]].isna().to_numpy().mean() * 100),
            "currency_missing_percent": float(subset.currency.isna().mean() * 100),
            "price_scope_undocumented_percent": float(subset.price_scope.eq("unknown").mean() * 100),
        }
        any_eligible = False
        for name in COHORTS[:2]:
            rows = frames[name]
            fit = rows[rows.split.isin(["train", "validation"])]
            fit = fit[fit.origin.eq(code) | fit.destination.eq(code)]
            cells = supports[name]
            cells = cells[cells.origin.eq(code) | cells.destination.eq(code)]
            item[name + "_observations"] = int((subset.cohort == name).sum())
            item[name + "_fit_observations"] = len(fit)
            item[name + "_fit_quote_groups"] = fit.quote_group.nunique()
            item[name + "_fit_collection_days"] = fit.collection_date.nunique()
            item[name + "_largest_profile"] = int(cells["n"].max()) if len(cells) else 0
            item[name + "_eligible_profiles"] = int(cells.eligible.sum())
            any_eligible |= bool(cells.eligible.any())
        item["research_eligible"] = any_eligible
        item["production_eligible"] = False
        item["serving_reason"] = (
            "Cabin research has >=50 fitting observations in an exact profile; unknown semantics still block production."
            if any_eligible else
            "No cabin fitting records; network exact profiles have fewer than 50 observations. Unverified semantics also block production."
        )
        records.append(item)
    eligibility = pd.DataFrame(records)
    eligibility.to_csv(REPORTS / "airport_serving_eligibility_audit.csv", index=False)
    # Compare the 2019 distributions on common explicit observation keys.
    folder = ROOT / "data/raw/phase2"
    reference = pd.read_excel(folder / "prithvirajshukla__flight-fare-prediction/Flight_Fare.xlsx")
    common = ["Airline", "Source", "Destination", "Price"]
    others = [
        ("viveksharmar", pd.read_csv(folder / "viveksharmar__flight-price-data/flight_dataset.csv")),
        ("ankushsonar", pd.read_csv(folder / "ankushsonar__flight-price-dataset-india-2019/Flight_data.csv")),
    ]
    duplicates = {}
    for name, other in others:
        duplicates[name] = {
            "rows": len(other),
            "same_order_common_key_fraction": float((other[common].astype(str).to_numpy() ==
                                                       reference[common].astype(str).to_numpy()).all(axis=1).mean()),
            "key": common,
        }
    cleaned = pd.read_csv(folder / "sshriya08__flight-price-prediction-dataset/flight_cleaned.csv")
    duplicates["sshriya08"] = {
        "rows": len(cleaned), "origin_labels": sorted(cleaned.From.unique()),
        "destination_labels": sorted(cleaned.To.unique()),
        "booking_days": cleaned.Booking_date.nunique(),
        "added_booking_hour_column": "Booking_Hour" in cleaned,
        "booking_hour_provenance": "not documented in dataset card",
    }
    dump(OUT / "candidate_overlap.json", duplicates)
    dump(OUT / "serving_domain_check.json", domain)
    dump(OUT / "baseline_reconciliation.json", {
        "immutable_files_checked": len(immutable), "all_original_data_and_models_unchanged": all(immutable.values()),
        "evaluation": evaluation, "observed_airports": len(codes),
        "research_eligible_airports": int(eligibility.research_eligible.sum()),
        "research_ineligible_airports": int((~eligibility.research_eligible).sum()),
        "production_eligible_airports": 0,
    })
    # Future promotion must satisfy these independently; no existing values are relabeled.
    semantics = {}
    for name, data in frames.items():
        semantics[name] = {
            "source": data.source_dataset.iloc[0], "currency": None,
            "currency_status": "undocumented", "mixed_currency_status": "cannot rule out or test",
            "price_scope": "unknown", "passenger_basis": "unknown",
            "booking_journey_type": "unknown", "record_shape": "single_direction_record",
            "cabin_labels": sorted(data.cabin_class.unique()),
            "collection_dates": sorted(data.collection_date.dt.strftime("%Y-%m-%d").unique()),
            "travel_dates": [str(data.travel_date.min().date()), str(data.travel_date.max().date())],
            "source_price_field": "Price" if name == "cabin_2023" else "Fare",
            "official_card_snapshot": str(
                OUT / ("card_" + data.source_dataset.iloc[0].replace("/", "__") + ".json")
            ).replace(str(ROOT) + "\\", ""),
            "production_eligible": False,
        }
    dump(OUT / "fare_semantics.json", semantics)
    target = """# Prediction target decision (before diagnostic fitting)

The existing target remains the source-recorded numeric fare, isolated by collector.
No selected source's currency, tax/fee scope, passenger count or booking journey type
was established from its original card, public file metadata or raw records. No FX
conversion or INR relabeling is justified. Newly inspected files do not provide a
compatible authentic total-fare target. Existing data and models will be retained.

A future product target should be a documented INR total per adult passenger for
one specified one-way itinerary and cabin, with known taxes/fees, query timestamp,
departure date and source reuse rights. Genuine return targets require an actual
whole-return quote and return date. Base fares/aggregates require separate targets.

Full production retraining is not justified. Additional fitting, if performed in
this phase, is development-only support sensitivity and two-airport generalization,
using the unchanged research target. It cannot change the frozen serving artifact
or use the final test to select a new rule. A fresh independent evaluation and
documented fare semantics are required before promotion.

The cabin artifact fits lead days 1–35, calibrates on 36–40, and tests on 41–50.
Zero of its final-test rows passes the current serving ranges. Therefore the old
aggregate interval coverage is offline evidence, not validation for a served
scenario. Intervals will be withheld from responses; point research estimates and
historical offline metrics remain available.
"""
    (REPORTS / "prediction_target_decision.md").write_text(target, encoding="utf-8")
    print(json.dumps({"airports": len(codes), "eligible": int(eligibility.research_eligible.sum()),
                      "domain": domain, "overlap": duplicates}, indent=2))


if __name__ == "__main__":
    main()
