"""Development-only sensitivity and explicit one/both-unseen-airport diagnostics."""
import json
import sys
from pathlib import Path

import pandas as pd
from catboost import CatBoostRegressor

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
from skylens.features import CATEGORICAL, feature_frame
from skylens.train import metrics
from phase2_audit import load_cohort, KEYS


def fit(data, params):
    model = CatBoostRegressor(**params, loss_function="MAE", random_seed=42,
                             thread_count=8, verbose=False, allow_writing_files=False)
    model.fit(feature_frame(data), data.price, cat_features=CATEGORICAL)
    return model


def main():
    assert (ROOT / "reports/prediction_target_decision.md").exists()
    threshold_rows, generalization = [], []
    for name in ["network_2020", "cabin_2023"]:
        meta = json.loads((ROOT / f"models/{name}/metadata.json").read_text())
        params = {**meta["hyperparameters"], "iterations": 250}
        data = load_cohort(name)
        train = data[data.split.eq("train")]
        validation = data[data.split.eq("validation")]
        model = fit(train, params)
        validation = validation.copy()
        validation["diagnostic_prediction"] = model.predict(feature_frame(validation))
        support = train.groupby(KEYS).size().rename("training_n").reset_index()
        evaluated = validation.merge(support, on=KEYS, how="left")
        for threshold in [5, 10, 20, 50, 100, 200]:
            cells = support[support.training_n.ge(threshold)]
            valid = evaluated[evaluated.training_n.ge(threshold)]
            row = {"cohort": name, "minimum_profile_count": threshold,
                   "fitting_airports": len(set(cells.origin) | set(cells.destination)),
                   "eligible_profiles": len(cells), "validation_rows": len(valid),
                   "validation_fraction": len(valid) / len(validation),
                   "iterations": 250, "numeric_bounds_applied": False,
                   "scope": "development diagnostic; not validated serving policy"}
            if len(valid):
                row.update(metrics(valid.price, valid.diagnostic_prediction))
            threshold_rows.append(row)
        print(name, "threshold diagnostic complete", flush=True)
        dev = data[data.split.isin(["train", "validation"])]
        counts = pd.concat([dev.origin, dev.destination]).value_counts()
        held = counts.index[:2].tolist()  # fixed from target-independent observation counts
        held_count = dev.origin.isin(held).astype(int) + dev.destination.isin(held).astype(int)
        fitting = dev[held_count.eq(0)]
        assert not set(held) & (set(fitting.origin) | set(fitting.destination))
        model = fit(fitting, params)
        for count, category in [(1, "one_unseen_endpoint"), (2, "both_endpoints_unseen")]:
            testing = dev[held_count.eq(count)]
            pred = model.predict(feature_frame(testing))
            generalization.append({
                "cohort": name, "category": category, "held_airports": "|".join(held),
                "training_rows": len(fitting), "iterations": 250,
                "evaluation_scope": "development only; not a final-artifact or deployment claim",
                **metrics(testing.price, pred),
            })
        print(name, "both-endpoint diagnostic complete", flush=True)
    pd.DataFrame(threshold_rows).to_csv(ROOT / "reports/serving_threshold_sensitivity.csv", index=False)
    pd.DataFrame(generalization).to_csv(ROOT / "reports/airport_generalization_phase2.csv", index=False)


if __name__ == "__main__":
    main()
