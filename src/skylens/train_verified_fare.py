"""Fit and evaluate a private CatBoost candidate from vetted one-way Economy quotes."""

import argparse
import json
from datetime import datetime
from math import sqrt
from pathlib import Path
from tempfile import TemporaryDirectory

from skylens.quotes import IST, ROOT, Quote, digest, encoded, locked, resolved_records, summary, temporal_split


class TrainingInputError(ValueError):
    """A safe description of an unavailable or unsuitable training input."""


CATEGORICAL = ["origin", "destination", "airline"]
FEATURES = [*CATEGORICAL, "departure_weekday", "days_to_departure"]
PARTITIONS = ("train", "validation", "calibration", "test")


def train_candidate(store: Path, manifest: Path, output: Path) -> dict:
    """Use a frozen split, and keep both the model and report in the private store."""
    store, manifest, output = store.resolve(), manifest.resolve(), output.resolve()
    if any(path == store or not path.is_relative_to(store) for path in (manifest, output)):
        raise TrainingInputError("The split and experiment must be inside the private quote store.")
    if output.exists():
        raise TrainingInputError("Choose an unused experiment directory.")
    with locked(store):
        records, _ = resolved_records(store)
        verified = sum(row["status"] == "verified_target" for row in records)
        if not verified:
            raise TrainingInputError("No verified fare observations in the quote store.")
        if summary(store)["verified_targets"] != verified:
            raise TrainingInputError("Quote evidence or retention is invalid. Review the quote store before training.")
        split = json.loads(manifest.read_text(encoding="utf-8"))
        dataset_hash = digest(encoded(records))
        if split.get("dataset_sha256") != dataset_hash:
            raise TrainingInputError("Frozen split does not match the current quote store.")
        boundaries = [datetime.fromisoformat(value) for value in split["boundaries_utc"]]
        verified_split = temporal_split(records, boundaries)
        if verified_split["assignments"] != split.get("assignments"):
            raise TrainingInputError("Frozen assignments do not match the chronological, shared-segment split.")

        # Validate the split on the full store before restricting the price target.
        quotes = [Quote.model_validate(row["quote"]) for row in records if row["status"] == "verified_target"]
        rows = {
            quote.quote_id: {
                "origin": quote.origin_airport,
                "destination": quote.destination_airport,
                "airline": quote.airline,
                "departure_weekday": quote.departure_date.weekday(),
                "days_to_departure": (quote.departure_date - quote.collected_at_utc.astimezone(IST).date()).days,
                "amount_inr": float(quote.displayed_total),
            }
            for quote in quotes if quote.journey_type == "one_way" and quote.cabin_class.lower() == "economy"
        }
        partitions = {
            name: [rows[quote_id] for quote_id in verified_split["assignments"][name] if quote_id in rows]
            for name in PARTITIONS
        }
        if any(not part for part in partitions.values()):
            raise TrainingInputError("Each split needs verified one-way Economy quotes after shared-flight purging.")
        if len({row["amount_inr"] for row in partitions["train"]}) < 2:
            raise TrainingInputError("Fitting needs more than one distinct observed fare in the training split.")

        model, metrics, test_profiles = _fit_and_evaluate(partitions)
        output.parent.mkdir(parents=True, exist_ok=True)
        with TemporaryDirectory(dir=output.parent, prefix=".candidate-") as work:
            stage = Path(work) / "result"
            stage.mkdir()
            artifact = stage / "model.cbm"
            model.save_model(str(artifact))
            report = {
                "target": "Selectable one-way Economy quote total for one adult, including taxes and fees",
                "features": FEATURES,
                "currency": "INR",
                "dataset_sha256": dataset_hash,
                "split_boundaries_utc": verified_split["boundaries_utc"],
                "purged_observations": len(verified_split["assignments"]["purged_cross_boundary"]),
                "model_sha256": digest(artifact.read_bytes()),
                "partitions": metrics,
                "test_profiles": test_profiles,
                "serving_approved": False,
            }
            (stage / "evaluation.json").write_bytes(encoded(report))
            stage.rename(output)
    return report


def _fit_and_evaluate(partitions: dict):
    import pandas as pd
    from catboost import CatBoostRegressor

    train = pd.DataFrame(partitions["train"])
    model = CatBoostRegressor(iterations=300, depth=6, loss_function="MAE", random_seed=42,
                             thread_count=2, verbose=False, allow_writing_files=False)
    # Fix parameters in advance. Only the training partition contributes to the fit.
    model.fit(train[FEATURES], train["amount_inr"], cat_features=CATEGORICAL)
    cohorts = train.groupby(CATEGORICAL).agg(
        baseline=("amount_inr", "median"),
        first_lead=("days_to_departure", "min"),
        last_lead=("days_to_departure", "max"),
    ).reset_index()
    metrics = {}
    test_profiles = []
    for name, rows in partitions.items():
        sample = pd.DataFrame(rows).merge(cohorts, how="left", on=CATEGORICAL, validate="many_to_one")
        # Price error is comparable to a route/carrier baseline only in fitted cohorts.
        comparable = sample[sample["days_to_departure"].between(sample["first_lead"], sample["last_lead"])]
        scores = {"observations": len(sample), "within_training_support": len(comparable)}
        if not comparable.empty:
            comparable = comparable.assign(error=model.predict(comparable[FEATURES]) - comparable["amount_inr"])
        scores.update(_error_metrics(comparable))
        metrics[name] = scores
        if name == "test":
            for key, group in sample.groupby(CATEGORICAL):
                supported = comparable.loc[comparable.index.intersection(group.index)]
                test_profiles.append({**dict(zip(CATEGORICAL, key)), "observations": len(group),
                                      "within_training_support": len(supported), **_error_metrics(supported)})
    return model, metrics, test_profiles


def _error_metrics(sample) -> dict:
    if sample.empty:
        return dict.fromkeys(("mae_inr", "rmse_inr", "median_absolute_error_percent", "baseline_mae_inr"))
    errors = sample["error"]
    return {"mae_inr": float(errors.abs().mean()), "rmse_inr": sqrt(errors.pow(2).mean()),
            "median_absolute_error_percent": float(100 * (errors.abs() / sample["amount_inr"]).median()),
            "baseline_mae_inr": float((sample["baseline"] - sample["amount_inr"]).abs().mean())}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--store", type=Path, default=ROOT / "data/quotes")
    parser.add_argument("--split", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    try:
        report = train_candidate(args.store, args.split, args.output)
    except TrainingInputError as error:
        parser.exit(1, f"{error}\n")
    except (ValueError, TypeError, KeyError, RuntimeError, OSError):
        parser.exit(1, "Training stopped. Check the private split, quote store and local model dependencies.\n")
    print(json.dumps(report, indent=2))


if __name__ == "__main__":
    main()
