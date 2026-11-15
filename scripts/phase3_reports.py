"""Build Phase 3 evidence from the untouched baseline and actual quote store.

No acquisition, training, model mutation or fabricated quote generation.
"""
import csv
import hashlib
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
sys.path.insert(0, str(ROOT))
from skylens.quotes import summary
from backend.app.schemas import PredictionRequest


def load(path):
    return json.loads((ROOT / path).read_text(encoding="utf-8"))


def table(rows, fields):
    return "\n".join(["| " + " | ".join(fields) + " |", "| " + " | ".join("---" for _ in fields) + " |"]
                     + ["| " + " | ".join(str(row.get(f, "")) for f in fields) + " |" for row in rows])


def write(name, text):
    (ROOT / "reports" / name).write_text(text.strip() + "\n", encoding="utf-8")


def main():
    checkpoint = load("data/metadata/phase3_checkpoint.json")
    baseline = load(checkpoint["checkpoint_dir"] + "/baseline_manifest.json")["files"]
    frozen = {name: hashlib.sha256((ROOT / name).read_bytes()).hexdigest() == value["sha256"]
              for name, value in baseline.items()
              if name.startswith(("data/raw/", "data/processed/", "data/interim/", "models/"))}
    assert all(frozen.values()), "An original data/model artifact changed"
    models = []
    for cohort in ["cabin_2023", "network_2020"]:
        meta = load(f"models/{cohort}/metadata.json")
        sha = hashlib.sha256((ROOT / f"models/{cohort}/model.cbm").read_bytes()).hexdigest()
        assert sha == meta["artifact_sha256"]
        models.append({"model": cohort, "sha256": sha, **meta["test_metrics"]})
    quality = summary(ROOT / "data/quotes")
    # Reports below describe the source-access result of this phase. Refuse to
    # silently reuse its zero-observation conclusions after new data is supplied.
    assert quality["raw_rows"] == 0, "New quotes require a new semantic/statistical review before report generation"
    with (ROOT / "reports/airport_serving_eligibility_audit.csv").open(encoding="utf-8", newline="") as inp:
        old = {r["iata_code"]: r for r in csv.DictReader(inp)}
    with (ROOT / "reports/airport_fare_coverage.csv").open(encoding="utf-8", newline="") as inp:
        airports = list(csv.DictReader(inp))
    eligible = sorted(r["iata_code"] for r in airports if r["any_research_eligible"] == "True")
    assert eligible == ["AMD", "BLR", "BOM", "CCU", "DEL", "HYD", "MAA"]
    audit = []
    for a in airports:
        prior = old.get(a["iata_code"], {})
        audit.append({"airport_ident": a["ident"], "iata_code": a["iata_code"], "name": a["name"],
                      "previous_endpoint_observations": a["fare_endpoint_observations"],
                      "new_verified_observations": 0, "new_verified_unique_itineraries": 0,
                      "total_verified_unique_itineraries": 0,
                      "historical_quote_group_proxy": prior.get("quote_groups", 0),
                      "historical_true_unique_itineraries": "not established" if prior else "no selected evidence",
                      "previous_unique_directional_routes": prior.get("directional_routes", 0),
                      "new_verified_routes": 0, "historical_airline_labels": prior.get("airline_labels", ""),
                      "historical_cabin_labels": prior.get("cabin_labels", ""), "new_verified_airlines": 0,
                      "new_verified_cabins": 0, "historical_collection_days": prior.get("collection_days", 0),
                      "historical_travel_start": prior.get("travel_start", ""), "historical_travel_end": prior.get("travel_end", ""),
                      "new_collection_days": 0, "verified_currency": "no new verified target",
                      "price_definition": "historical unknown; no new all-in single-adult target",
                      "statistical_support": "no additional independent evidence",
                      "research_eligible_unchanged": a["any_research_eligible"], "production_eligible": False,
                      "decision": "retain historical research eligibility" if a["any_research_eligible"] == "True" else "unsupported; no qualifying additional evidence"})
    with (ROOT / "reports/new_airport_evidence.csv").open("w", encoding="utf-8", newline="") as out:
        writer = csv.DictWriter(out, fieldnames=list(audit[0])); writer.writeheader(); writer.writerows(audit)
    pairs = [("DEL", "BOM"), ("BOM", "BLR"), ("BLR", "HYD"), ("HYD", "MAA"),
             ("MAA", "CCU"), ("CCU", "AMD"), ("AMD", "DEL"), ("BOM", "PNQ"),
             ("DEL", "GAU"), ("BLR", "COK"), ("DEL", "IXZ"), ("DEL", "JAI")]
    with (ROOT / "reports/route_fare_coverage.csv").open(encoding="utf-8", newline="") as inp:
        routes = list(csv.DictReader(inp))
    plan = []
    for origin, destination in pairs:
        selected = [r for r in routes if r["origin"] == origin and r["destination"] == destination]
        assert selected, "Plan must be grounded in observed routes"
        cabin = sum(int(r["observations"]) for r in selected if r["source_dataset"].startswith("yashdharme36/") and r["cabin_class"] != "First")
        network = sum(int(r["observations"]) for r in selected if r["source_dataset"].endswith("fare-details-2020"))
        challenge = sum(int(r["observations"]) for r in selected if r["source_dataset"].endswith("fare-travel-listings"))
        plan.append({"route": origin + "-" + destination, "cabin_2023_rows_excluding_First": cabin,
                     "network_2020_rows": network, "later_challenge_rows": challenge,
                     "stratum": "both eligible historically" if origin in eligible and destination in eligible else "extension research only"})
    with (ROOT / "config/quote_route_plan.csv").open("w", encoding="utf-8", newline="") as out:
        writer = csv.DictWriter(out, fieldnames=list(plan[0])); writer.writeheader(); writer.writerows(plan)
    evidence = {"recorded_at_utc": datetime.now(timezone.utc).isoformat(), "checkpoint": checkpoint,
                "unchanged_data_model_files": len(frozen), "all_unchanged": all(frozen.values()),
                "models": models, "eligible_airports": eligible, "minimum_profile_support": 50,
                "quote_summary": quality, "retraining_performed": False,
                "prediction_intervals": "withheld_unvalidated_serving_domain",
                "prediction_request_schema": PredictionRequest.model_json_schema()}
    (ROOT / "data/metadata/phase3").mkdir(exist_ok=True)
    (ROOT / "data/metadata/phase3/baseline_and_decision.json").write_text(json.dumps(evidence, indent=2), encoding="utf-8")
    write("quote_collection_plan.md", f"""
# Repeatable quote-collection experiment

Status: preregistered design, **not executed**. No source has a recorded collection/storage/ML grant. Begin only after the [access audit](quote_source_access_audit.md) dependencies are resolved. No paid calls or tickets are part of this design.

## Route selection from actual evidence

The historical directory has 661 airfields, 165 IATA codes, 88 observed fare endpoints and seven research-eligible airports: {', '.join(eligible)}. The following 12 directional routes are present in actual historical files. Seven form a cycle covering all eligible airports. Five extension routes add western, northeastern, southern, island and northern observations without claiming service or serving eligibility. Historical network/challenge observations remain distinct; neither establishes current schedules or verified prices.

{table(plan, list(plan[0]))}

## Sampling unit and repeatable schedule

An itinerary is a fixed set of flight segments on actual departure/return dates, with cabin, fare family, baggage/refund conditions and passenger composition held constant for comparisons. A snapshot is one source offer at one query instant. A collection day is its India-local calendar date. Shared segments connect dependent observations even across different cabins, sources and genuine return products. Same-day refreshes remain history, not extra independent samples.

After permission, make a route/carrier availability inventory using the authorized interface. Record no-service/unavailable/permission-denied outcomes without inventing prices or silently substituting another route/carrier. Historical GO FIRST/Vistara labels do not establish current services. Select actual available carriers, aiming for two distinct marketing carriers per route where authorized availability permits, and distinguish operating carriers. Start with a single adult, no loyalty/corporate/student discounts, fixed market/currency and explicit mandatory fees. Preserve promotion/fare-family/baggage differences; compare matched products only.

A logistics pilot selects four distinct departure dates per route (two weekdays, two weekend dates) across at least four collection weeks: up to 48 route/departure cells before carrier/class expansion. Rotate early (05:00–11:59), midday (12:00–17:59) and evening (18:00–23:59) **departure** periods across dates. Collect at a fixed 10:00 IST session, with actual timestamp recorded and randomized route order; a missed session is missing data. This pilot size is a balanced workload allocation, **not** a sufficient ML sample or a precision claim.

Anchor each fixed itinerary at 35 days before departure where visible. Repeat its authorized offer at leads 28, 21, 14, 7, 3 and 1 days, retaining the same segments/product. Add rolling departure cohorts to observe several leads on the same collection date; this helps separate lead-time effects from calendar shocks. Include multiple collection weekdays over at least four weeks for the pilot; expand the day span based on estimated date correlation. A collection date can induce common shocks, so different dates are not assumed statistically independent simply because they differ.

Economy is the starting cohort. Add actual Business/Premium Economy cells only when the route/carrier sells them with permission; log absence, never map a fare brand to a cabin by guess. First remains outside the current model. A separate return arm uses a **single actual return offer** with fixed outbound/inbound flights and stay length. Pair it with separately recorded compatible outbound/inbound one-way offers only if all three products and total semantics are independently evidenced. Do not create return targets by addition. Journey types remain separate target strata.

Apply the source's daily limits to **all raw observations**, including refreshes and malformed entries, and stop rather than circumvent a rate/access gate. Keep a private session log with planned cell, actual timestamp, result status and reason; unavailable results are not zero-price observations. No external collector runs automatically.

## Statistical stopping and validation budget

Set precision and practically meaningful improvement before seeing the final test. For an overall interval-coverage proportion, approximate 95% precision of ±5 percentage points requires `ceil(1.96² × p(1-p) / 0.05²)`: **139 independent test units** if p=0.9 is an adequate planning estimate, or **385** using conservative p=0.5. Use Wilson/exact binomial intervals when reporting actual coverage, not the approximation as a guarantee. These are overall evaluation-planning numbers, not training minima or a rule that 385 snapshots validate every airport. Each claimed subgroup needs its own justified precision and multiplicity treatment. [NIST sample-size guidance](https://www.itl.nist.gov/div898/handbook/ppc/section3/ppc333.htm), [binomial confidence limits](https://www.itl.nist.gov/div898/handbook/prc/section2/prc241.htm).

For mean absolute error, use pilot cluster-level error variability `s` and a preregistered absolute tolerance `delta`: planning `n ≈ (1.96*s/delta)²`. Neither `s` nor an INR improvement threshold can be estimated from zero quotes or from legacy source units. For repeat measurements, estimate itinerary/day correlation and use itinerary and collection-day block bootstrap or multiway clustering; a simple balanced-cluster approximation is `DEFF = 1+(m-1)*rho`. Do not plug in an invented correlation or treat repeated refreshes as n. Expand the number of distinct itineraries/days until uncertainty and intended subgroup coverage are adequate. Sparse strata remain unsupported.

Use separate chronological training, tuning-validation, calibration and final-test windows chosen before final targets are opened. Collect fresh itinerary cohorts in every window; shared-segment components spanning windows are purged by the split tool. Keep the final test sealed from feature/hyperparameter/threshold selection and never calibrate on it. Need counts **after** purging, not raw counts. The initial 48-cell logistics pilot cannot fulfill the independent final-test plan, calibration requirement or nationwide coverage. If feasible zero-cost authorized access cannot meet this design, report insufficient evidence and retain the existing models.
""")
    write("quote_data_quality_report.md", f"""
# Quote data quality

Computed from the actual private quote store, not unit-test fixtures.

{table([quality], list(quality))}

No source passed the access/retention/reuse gate during Phase 3. No quote CSV was ingested, so currency-verified totals, known taxes, known passenger basis and genuine return targets each number **zero**. Missingness percentages, acceptance rates and duplication rates are undefined with no actual input; zero rows is not a 100% quality score. The header-only template is not evidence. Synthetic software fixtures live only in temporary test directories and never enter this store or training.

The importer preserves authorized raw bytes, source permission snapshots and evidence hashes; checks schema/time/price/product consistency; separates research-only and quarantined rows; rejects unapproved access before retaining payload; preserves repeat snapshots and excludes conflicts. Tests exercise these behaviors using explicitly synthetic fixtures. A passing software test does not demonstrate source authenticity or a model-quality improvement. See [manual instructions](../docs/QUOTE_COLLECTION_GUIDE.md).
""")
    write("quote_variability_analysis.md", """
# Repeated quote variability

**Not estimable: zero actual new observations, zero independent itinerary groups and zero new collection days.** There are no fare changes, standard deviations, confidence intervals, carrier/class differences, lead-window trends or compatible return/one-way ratios to calculate. No example prices, toy charts or synthetic trends stand in for evidence.

The original single-query-day 2023 cohort cannot identify query-time fare movement independently from departure-date effects. The 2020 network dates are a different, semantically unverified cohort. They cannot fill the new dataset or establish live INR variability.

Once licensed observations exist, resolve conflicts and deduplicate exact source/itinerary/time snapshots, retaining all other history. Match segments, cabin, fare family, baggage/refund terms, passenger composition, currency, total scope and source. Use one preregistered 10:00 IST observation per itinerary/day for daily comparisons; retain incidental refreshes outside the independence count. Report matched pair counts, distinct itineraries/dates and missing/unavailable outcomes alongside differences, percent changes and robust quantiles. A two-point change is descriptive only, not a population variance estimate.

Estimate carrier/class/route/lead effects only with overlapping matched sampling cells; disclose confounding and sparse groups. For compatible return comparisons, report the actual return offer separately from the sum of the independently evidenced one-way offers; that comparison is not itself a return target. Use itinerary/date blocks for uncertainty and calendar drift checks. The [sampling plan](quote_collection_plan.md) defines precision planning; no universal sample threshold is declared from empty data.
""")
    write("new_airport_evidence_report.md", f"""
# Airport evidence after Phase 3

**No airport changed eligibility.** Verified new observations: 0. Historical fare endpoints: 88. Research-eligible endpoints: {', '.join(eligible)}. Production-eligible endpoints: 0.

[new_airport_evidence.csv](new_airport_evidence.csv) records every one of the {len(airports)} directory records, including airfields with no IATA code or fare evidence. It carries previous endpoint observation counts, directional routes, airline/cabin labels, collection/travel coverage, historical quote-group proxies, new verified observations/itineraries/routes/carriers/classes/days, currency/price definition, statistical support and the unchanged decision. No previous rows are reclassified as verified INR targets.

True historical unique booking-itinerary counts are not established by undocumented single-direction rows; their quote-group proxy is explicitly separate. New verified itinerary count and total **verified** itinerary count are both zero. Adding endpoint observations across incompatible source cohorts would not yield a valid independent sample size.

The exact `(origin,destination,airline,cabin_class,stops)` fitting-support threshold remains 50, with existing per-cell numeric bounds. It is an operational safeguard, not proof of statistical reliability. New airport support would need source-semantic compatibility, distinct itineraries and dates, profile coverage and independent subgroup validation. More airport metadata or repeated refreshes cannot supply that evidence. No threshold reduction, automatic training ingestion or new serving option was made.
""")
    write("phase3_retraining_decision.md", """
# Phase 3 retraining decision

**Do not retrain.** No new verified quote or additional airport/carrier/class/journey evidence was acquired. There is no compatible new target or independent evaluation sample with which to demonstrate improvement. Existing data remain isolated historical cohorts with unknown currency, tax scope, passenger basis and booking journey type. The new INR all-in single-adult intake target must not be appended to source-unit labels.

No full training, diagnostic model fitting, hyperparameter search, model replacement or serving-threshold change occurred. Both original native model hashes and metadata are preserved. Reproducibility instructions explain how to fit a separate local reconstruction when needed; that is not a new training run in this phase.

A future separate experiment needs reviewed source/ML rights, evidence-bound targets, measured overlap/conflicts, a frozen target definition and grouped chronological training/validation/calibration/final-test partitions with sufficient post-purge support. Use development-only unseen-route and held-airport studies with one/both endpoints unseen, followed by fresh untouched tests for any expanded scope. Report per-route/airport/carrier/cabin/lead/journey error and uncertainty. Promote only a meaningful preregistered improvement on compatible targets without subgroup regression; retain the old artifact otherwise. Historical source-unit errors cannot be described as INR errors or directly compared with new all-in totals.

Prediction intervals remain withheld. A future conformal experiment must calibrate inside the intended accepted domain, separately from tuning/final test, then measure empirical coverage/width and uncertainty on fresh independent groups and relevant subgroups. Temporal shift/shared snapshots break the simple exchangeability premise; a nominal 90% level is not a guarantee under drift. [Conformal prediction beyond exchangeability](https://arxiv.org/abs/2202.13415) discusses this limitation. No new interval evidence exists here.
""")
    write("phase3_model_validation.md", f"""
# Phase 3 model preservation and validation

Direct pre-change baseline: **48 Python tests passed**, one upstream deprecation warning. Local checkpoint: `{checkpoint['checkpoint_dir']}`; archive SHA-256 `{checkpoint['archive_sha256']}`. Rechecked {len(frozen)} original raw/processed/interim/model files: all unchanged. Model metadata and support profiles are included in that comparison.

{table(models, ['model', 'sha256', 'n', 'mae', 'rmse', 'r2'])}

Metrics are the original measured offline final-test results in **source fare units**, not newly obtained or current INR accuracy. Model-loading/native prediction/SHAP regression checks are retained. Phase 3 final test/build/HTTP outcomes are recorded in [final findings](phase3_final_findings.md).

## Unchanged contract

Research serving remains limited to 592 exact eligible profiles across seven cabin-cohort airports and 42 directional routes. Wider-network exact fitting profiles never reach 50; its model remains offline only. Requests require `research_acknowledged=true`, known model/airports/carrier/cabin/stops, distinct endpoints and per-profile numeric support. Unknown extra fields, return/multicity booking inputs, passenger counts and unsupported airports are rejected. `journey_type` remains `single_direction_record`; estimates have currency null and unknown price/passenger scope. The actual request JSON schema is saved in [baseline_and_decision.json](../data/metadata/phase3/baseline_and_decision.json).

The 1e-9-hour representation tolerance remains unchanged; a real out-of-range minute is still rejected. Intervals remain null with `withheld_unvalidated_serving_domain`. The legacy cabin final test has no rows inside current accepted numeric support, so its offline nominal coverage cannot validate an accepted request. No new INR estimate, genuine return prediction, live price, nationwide coverage or production readiness is claimed.

## New-data protocol

Use collection timestamps for four sequential windows. Union all records sharing a physical segment, including different source/cabin/fare/return representations; purge components spanning a boundary. Freeze dataset hash, boundaries and assigned IDs before fitting. All preprocessing and feature selection learn from training only; tuning uses validation only; calibration is separate; final test is untouched. API-time features must be available at quote time, never later availability/purchase outcomes or a future price. The importer does not invoke any training or serving code. Zero new quotes means no new-data accuracy/leakage/generalization claim can be made. Synthetic software split tests check grouping logic only.
""")
    print(json.dumps({"frozen_files": len(frozen), "eligible_airports": eligible, "quote_summary": quality}))


if __name__ == "__main__":
    main()
