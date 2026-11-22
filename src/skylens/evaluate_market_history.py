"""Read-only replay of native historical research models. Results are in original source units."""
import json
from math import ceil

import numpy as np
import pandas as pd
from catboost import CatBoostRegressor

from skylens.features import CATEGORICAL, FEATURES, feature_frame
from skylens.quotes import ROOT, digest
from skylens.train import metrics, temporal_split


def replay(cohort):
    directory = ROOT / "models" / cohort
    meta = json.loads((directory / "metadata.json").read_text(encoding="utf-8"))
    target = ROOT / f"data/processed/{cohort}.parquet"
    artifact = directory / "model.cbm"
    if digest(target.read_bytes()) != meta["processed_sha256"] or digest(artifact.read_bytes()) != meta["artifact_sha256"]:
        raise ValueError("Research artifact or original processed observations changed.")
    model = CatBoostRegressor()
    model.load_model(str(artifact))
    if (FEATURES != meta["features"] or FEATURES != model.feature_names_
            or CATEGORICAL != meta["categorical_features"]
            or model.get_cat_feature_indices() != [FEATURES.index(col) for col in CATEGORICAL]):
        raise ValueError("Native artifact feature order or categorical encoding changed.")
    data = pd.read_parquet(target)
    data = data.loc[~data.cabin_class.isin(meta["rare_classes_excluded"])].copy()
    data, split = temporal_split(data, cohort)
    if split != meta["split_protocol"]:
        raise ValueError("Original temporal split boundaries or purged row count changed.")
    partitions = data[data.split.isin(["train", "validation", "calibration", "test"])]
    if (partitions.groupby("quote_group").split.nunique().max() != 1
            or partitions.groupby("fingerprint").split.nunique().max() != 1
            or partitions.split.value_counts().to_dict() != meta["split_sizes"]):
        raise ValueError("Historical split sizes or quote-group isolation changed.")
    test = data[data.split.eq("test")]
    calibration = data[data.split.eq("calibration")]
    prediction = model.predict(feature_frame(test))
    archived = pd.read_parquet(ROOT / f"reports/{cohort}_test_predictions.parquet")
    np.testing.assert_array_equal(test.fingerprint, archived.fingerprint)
    np.testing.assert_allclose(prediction, archived.prediction, rtol=0, atol=1e-8)
    error = metrics(test.price, prediction)
    for key, value in error.items():
        np.testing.assert_allclose(value, meta["test_metrics"][key], rtol=0, atol=1e-8)
    error["mean_signed_error"] = float((prediction - test.price).mean())
    residuals = abs(calibration.price - model.predict(feature_frame(calibration)))
    level = min(1, ceil((len(residuals) + 1) * meta["interval"]["nominal_coverage"]) / len(residuals))
    q = float(np.quantile(residuals, level, method="higher"))
    coverage = float(test.price.between(np.maximum(0, prediction - q), prediction + q).mean())
    np.testing.assert_allclose([q, coverage], [meta["interval"]["residual_quantile"], meta["interval"]["test_coverage"]],
                               rtol=0, atol=1e-8)
    support = pd.read_csv(directory / "support.csv")
    keys = ["origin", "destination", "airline", "cabin_class", "stops"]
    eligible = support[support.eligible]
    within = test.merge(eligible, on=keys, validate="many_to_one")
    for field, lower, upper in [("days_left", "lead_min", "lead_max"), ("duration_minutes", "duration_min", "duration_max"),
                                ("departure_hour", "hour_min", "hour_max")]:
        within = within[within[field].between(within[lower], within[upper])]
    recorded = json.loads((ROOT / "data/metadata/phase2/serving_domain_check.json").read_text())[cohort]
    if len(eligible) != recorded["eligible_cells"] or len(within) != recorded["test_rows_inside_current_serving_domain"]:
        raise ValueError("Historical profile eligibility or holdout support changed.")
    return {"cohort": cohort, "unit": meta["unit"], "currency": meta["currency"], "price_scope": meta["price_scope"],
            "passenger_basis": meta["passenger_basis"], "journey_types": meta["journey_types"],
            "production_ready": meta["production_ready"], "research_only": meta["research_only"],
            "eligible_research_profiles": len(eligible), "test_rows_inside_research_domain": len(within),
            **error, "historical_interval_coverage": coverage}


if __name__ == "__main__":
    print(json.dumps([replay(c) for c in ("cabin_2023", "network_2020")], indent=2))
