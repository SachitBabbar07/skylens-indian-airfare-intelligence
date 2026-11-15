# Phase 3 model preservation and validation

Direct pre-change baseline: **48 Python tests passed**, one upstream deprecation warning. Local checkpoint: `backups/phase3_20261115T070212Z`; archive SHA-256 `d0816b136afc7a3fce071d6ef0583b656f00767a59fa263726fc7f3e49490845`. Rechecked 56 original raw/processed/interim/model files: all unchanged. Model metadata and support profiles are included in that comparison.

| model | sha256 | n | mae | rmse | r2 |
| --- | --- | --- | --- | --- | --- |
| cabin_2023 | feaeadb9f82931f8aa048bf686ac0db7c9b178d3aa46fd219237a4e4df6b737f | 88773 | 2339.7568244890613 | 4376.351778545567 | 0.9470333889343409 |
| network_2020 | 9c98ad32b7f445cf5900cd9362554d2a2422de44893568537e27aa320480a8ff | 5445 | 2764.6631279673315 | 4664.675451433455 | 0.4266470115210942 |

Metrics are the original measured offline final-test results in **source fare units**, not newly obtained or current INR accuracy. Model-loading/native prediction/SHAP regression checks are retained. Phase 3 final test/build/HTTP outcomes are recorded in [final findings](phase3_final_findings.md).

## Unchanged contract

Research serving remains limited to 592 exact eligible profiles across seven cabin-cohort airports and 42 directional routes. Wider-network exact fitting profiles never reach 50; its model remains offline only. Requests require `research_acknowledged=true`, known model/airports/carrier/cabin/stops, distinct endpoints and per-profile numeric support. Unknown extra fields, return/multicity booking inputs, passenger counts and unsupported airports are rejected. `journey_type` remains `single_direction_record`; estimates have currency null and unknown price/passenger scope. The actual request JSON schema is saved in [baseline_and_decision.json](../data/metadata/phase3/baseline_and_decision.json).

The 1e-9-hour representation tolerance remains unchanged; a real out-of-range minute is still rejected. Intervals remain null with `withheld_unvalidated_serving_domain`. The legacy cabin final test has no rows inside current accepted numeric support, so its offline nominal coverage cannot validate an accepted request. No new INR estimate, genuine return prediction, live price, nationwide coverage or production readiness is claimed.

## New-data protocol

Use collection timestamps for four sequential windows. Union all records sharing a physical segment, including different source/cabin/fare/return representations; purge components spanning a boundary. Freeze dataset hash, boundaries and assigned IDs before fitting. All preprocessing and feature selection learn from training only; tuning uses validation only; calibration is separate; final test is untouched. API-time features must be available at quote time, never later availability/purchase outcomes or a future price. The importer does not invoke any training or serving code. Zero new quotes means no new-data accuracy/leakage/generalization claim can be made. Synthetic software split tests check grouping logic only.
