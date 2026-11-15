# SkyLens

Indian domestic airfare intelligence: historical estimation, airport coverage and native model explanations. FastAPI + React/TypeScript + CatBoost, with source-specific research cohorts and explicit limits.

> **Phase 3:** offline quote intake, evidence/permission gates and repeated-day sampling are implemented. Genuine new verified quotes: **0**. No retraining or airport expansion; seven research-eligible airports, 592 exact profiles, currency unknown for the historical models, intervals withheld. This is not a current INR fare or booking service. See [current findings](reports/phase3_final_findings.md).

## Start here

- [Installation, source-only CI and artifact reconstruction](docs/INSTALLATION.md)
- [Architecture walkthrough](docs/PROJECT_WALKTHROUGH.md), [data guide](docs/DATASET_GUIDE.md), [model guide](docs/ML_MODEL_GUIDE.md)
- [API](docs/API_GUIDE.md), [frontend](docs/FRONTEND_GUIDE.md), [explanations](docs/EXPLAINABILITY_GUIDE.md)
- [Quote entry instructions](docs/QUOTE_COLLECTION_GUIDE.md), [source access audit](reports/quote_source_access_audit.md), [sampling plan](reports/quote_collection_plan.md)
- [Contributing](CONTRIBUTING.md), [changelog](CHANGELOG.md), [GitHub delivery status](reports/github_delivery_report.md)

## Checks without datasets

Current local verification: **102 tests passed**, including the original 48; clean remote clone: **54 portable tests passed** plus production build. Authorized desktop/mobile browser QA now passes on ports 8000 and 5173, including native predictions and outage recovery. See [browser findings and genuine screenshots](reports/browser_qa_followup_20261115.md). Hosted CI stays skipped under the user's zero-spend decision. Repository details are in the [delivery report](reports/github_delivery_report.md).

Install `requirements-ci.txt` in Python 3.12, then run `python -m pytest tests/test_quotes.py tests/test_portable_contract.py -q`. Run `npm --prefix frontend ci` and `npm --prefix frontend run build` for the production UI. The [GitHub workflow](.github/workflows/ci.yml) uses synthetic software fixtures in temporary directories, never synthetic training data; it downloads no fare datasets. An actual remote CI result is reported only after a successful run, in the delivery report.

Raw/processed data, native models, private quote evidence and audit backups stay local. A clone is a reproducible **source** checkout; restoring exact artifacts or explicitly fitting a new research reconstruction is a separate step. No dependency automatically collects live fares, retrains at startup, or pays a service.

## License and attribution

The source repository is public by the owner's choice; the application runs locally. Raw datasets, native model binaries and private quote evidence remain excluded from Git.

Original code/documentation use the [MIT license](LICENSE). Third-party data, airport metadata, dependencies and learned artifacts retain their own rights; see [provenance](reports/dataset_licensing_and_provenance.md). The code license grants no airline collection, archive, redistribution or ML-use permission. Source URL/version/hash/schema/license summaries remain in the [registry](data/metadata/dataset_registry.json) and [frozen acquisition manifest](config/sources.json); individual source examples/full third-party snapshots are local only.

<!-- SKYLENS_PHASE2_NOTICE -->
> **Phase 2 baseline:** 48 tests passed; models and original data were preserved.
> Served intervals are withheld because the holdout does not validate the accepted
> input range. Currency/full fare scope remain unknown; browser QA was blocked at this baseline and has since passed the linked follow-up.
> See [phase-two findings](docs/PHASE2_FINDINGS.md) for the current status.
<!-- SKYLENS_PHASE2_NOTICE_END -->

Indian domestic historical airfare research, coverage and model explanations. A college ML project with traceable files, measured validation and a local application.

> Research edition: no verified current INR total-fare model qualified from the audited data. Currency, taxes, passenger basis and booking type remain undocumented. Outputs stay in source fare units. Confirmed one-way booking fares, round-trip/multi-city and live quotes are unsupported.

## Run locally (Windows PowerShell)
From this repository root, with free Python 3.12, Node 22+ and uv:

```powershell
.\setup.ps1
.\run.ps1
```

Open http://127.0.0.1:8000. API reference: http://127.0.0.1:8000/docs. The trained artifacts and datasets already exist in the original workspace; setup does not retrain. A source-only checkout needs separately authorized data/artifact reconstruction. Follow [installation](docs/INSTALLATION.md#source-only-research-reconstruction) before acquisition or training; these optional research commands change generated local files and are not required to install the quote importer or run portable CI.

Separate frontend development: start the API and run `npm --prefix frontend run dev`. Vite proxies API endpoints to port 8000. CORS allows only configured local origins. `.env.example` documents SKYLENS_CORS_ORIGINS, read from the process environment (the file is not automatically loaded). No account, paid API or secret is needed. Acquisition needs internet; subsequent inference is local. No cloud publication was performed.

## Evidence and scope
| concept | count |
| --- | --- |
| indian_airfield_records | 661 |
| with_iata | 165 |
| scheduled_flag | 120 |
| fare_airports | 88 |
| fare_origins | 66 |
| fare_destinations | 82 |
| fare_routes | 720 |
| production_eligible_airports | 0 |
| without_fare_evidence | 573 |

661 includes heliports/closed/noncommercial airfields. Scheduled flags are community metadata, not authoritative current schedules. The 88 observed airports are not 88 supported airports. The cabin model has 592 eligible exact profiles across seven airports and 42 routes. Every exact wider-network cell has fewer than 50 training observations, so that model is offline-evaluation-only. Economy, Business and Premium Economy appear in cabin research; First's 144 rows are excluded. Carrier availability is historical, not current service verification.

## Data discovery and selection
Sources were investigated across Kaggle, GitHub, Hugging Face, Zenodo, Figshare, OpenML, government and academic sources. Eight free public source archives and commit-pinned OurAirports metadata were inspected. Original cards, declared licenses, actual schemas, rows, sizes, hashes and exclusions are saved. Unknown target definitions mean the selected fares remain isolated research cohorts; normalized_price_inr is missing.

The 2023 raw EaseMyTrip source has seven cities and one collection day. Separate pre-pandemic PromptCloud records offer broader geography across three collection days. A later same-collector sample is a drift challenge, not independent compatible validation. Raw/cleaned representations are not stacked. The Goibibo candidate shifts the original 2022 dates 500 days with identical ordered flight IDs; it is excluded. Tax-exclusive base fares, aggregates, schedules and traffic are not mixed into an individual total-price target. See [discovery](reports/dataset_discovery_report.md), [selection](reports/dataset_selection_decision.md), [licenses](reports/dataset_licensing_and_provenance.md) and [coverage](reports/airport_coverage_report.md).

## Pipeline and architecture
Public archives → immutable raw files → audited canonical cohorts → leakage-controlled splits → candidate comparisons → fitted native models → FastAPI → React.

src/skylens separates preparation, feature schema, training and report generation; scripts separates acquisition. backend/app loads existing artifacts and validates requests; frontend retrieves metadata and renders real outputs. Model code and API serving are independent. Geography does not automatically validate unseen airports.

Preparation parses explicit duration/date values, preserves unknown scope/currency and records every exclusion. Native categorical labels are preserved. Training-only encoders/scalers and CatBoost fitting avoid full-data target statistics. Quote-group/fingerprint checks prevent cross-split duplicates. No final-test tuning, synthetic training data or guessed booking metadata is used. The single cabin collection date still confounds lead time and departure date.

## Models and actual results
Mean, median, Ridge, a decision tree and three CatBoost settings share identical temporal validation partitions. A small seeded parameter search selects the final model; final testing and calibration stay separate.

| cohort | n | mae | rmse | r2 | median_absolute_error | mape_percent | p90_absolute_error | interval_coverage |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| network_2020 | 5445 | 2764.6631 | 4664.6755 | 0.4266 | 1583.1307 | 23.0764 | 6464.8287 | 0.8516 |
| cabin_2023 | 88773 | 2339.7568 | 4376.3518 | 0.947 | 998.1895 | 13.7101 | 6142.7176 | 0.8924 |

Absolute errors use source fare units, not verified INR. R² is explained variance under the specified protocol, not accuracy. Cabin chronology tests later departures from one snapshot; network chronology tests the latest collection day. Random-group, route and unseen-airport stress fits use development data and cap tree count at 250, unlike final fits. [Evaluation](reports/model_evaluation_report.md), [errors](reports/error_analysis_report.md) and [external challenge](reports/external_validation_report.md) expose limits rather than relying only on R².

Native SHAP assigns actual fitted contributions: baseline + all contributions reproduces the output. Global mean absolute SHAP and validation permutation importance are saved. Contributions describe associations, not causes. [Explainability report](reports/explainability_report.md) includes an actual example. Residual intervals use separate calibration observations, with measured final-test coverage. Temporal shift prevents a distribution-free/future-price guarantee; optional ranges are labeled historical empirical intervals, not confidence intervals.

## API and interface
FastAPI validates schema, categories, joint support and numeric bounds. It hashes native model files at startup; requests never retrain. Errors return meaningful 422/503 or safe 500 responses without internal stacks. Explicit CORS is configurable. See [API guide](docs/API_GUIDE.md).

React + TypeScript + Vite offers searchable airports, dependent scenario fields, real model results and SHAP, a coverage directory and measured model tables. Backend metadata supplies every available option. A minimum 50 training observations is required per route/airline/class/stops profile, with observed numeric bounds; it is a conservative research heuristic, not a reliability theorem. Unsupported routes are blocked. Calendar-date inputs are omitted because current/future dates cannot be supported. API failure never falls back to fictional sample prices.

## Checks and reproducibility
The original Phase 1 suite had 40 tests; the current suite has 102 passing tests, including native prediction/SHAP, separation, corruption handling and support rejection. The production build and authorized desktop/mobile browser follow-up passed. Run `.venv\Scripts\python.exe -m pytest -q`; see the current browser report linked above.

Python packages are pinned in requirements.txt, npm in package-lock.json. Model metadata includes parameters, seed, dataset and artifact hashes, dates and metrics. Native artifacts/raw data are kept locally but ignored by Git to avoid unnecessary large-data redistribution. A source-only checkout must rerun acquisition/preparation/training. Never commit secrets or replace missing authentic fares with synthetic training rows.

## Learn and present
Start with [walkthrough](docs/PROJECT_WALKTHROUGH.md), [datasets](docs/DATASET_GUIDE.md), [pipeline](docs/DATA_PIPELINE_GUIDE.md), [models](docs/ML_MODEL_GUIDE.md), [SHAP](docs/EXPLAINABILITY_GUIDE.md), [API](docs/API_GUIDE.md), [frontend](docs/FRONTEND_GUIDE.md), [edge cases](docs/EDGE_CASES_AND_VALIDATION.md) and [viva preparation](docs/VIVA_PREPARATION.md). Reports and figures provide actual evidence.

## Remaining work and future improvements
A verified total-ticket service needs legitimately licensed quotes with currency, tax/passenger basis, real journey types and repeated query days. Wider serving needs more joint route evidence, compatible independent validation and current airline/airport verification. Real return fares are needed before round trips. First Class needs sufficient samples. Residual-interval shortfalls and external drift remain visible. Desktop/mobile viewport QA has passed; physical-device and cross-browser checks remain additional work. This deliverable is a working local research application, not a validated nationwide live-price service.


Additional executed checks: 592 advertised profiles passed real HTTP prediction with 0 failures; 2 compiled frontend assets and the HTML page returned HTTP 200. All 26 original file hashes match. Frozen-version acquisition was rerun successfully without raw overwrites. These historical HTTP checks were later supplemented by authorized browser QA.


## Additional cabin architecture diagnostic
| architecture | class | n | mae | rmse |
| --- | --- | --- | --- | --- |
| pooled | Business | 12788 | 5340.21 | 8557.315 |
| class_specific | Business | 12788 | 4751.384 | 7957.138 |
| pooled | Economy | 25231 | 1284.659 | 2103.226 |
| class_specific | Economy | 25231 | 1247.582 | 2067.501 |
| pooled | Premium Economy | 6661 | 1672.229 | 3044.729 |
| class_specific | Premium Economy | 6661 | 1339.922 | 2733.472 |
These are post-hoc development-only results. The frozen pooled artifact and its final-test results remain unchanged. Separate class models are a promising follow-up requiring a fresh untouched evaluation before promotion. Reproduce with `$env:PYTHONPATH = "src"` then `.venv\Scripts\python.exe scripts\compare_cabins.py`.
<!-- SKYLENS_PHASE2_START -->
## Phase-two findings — 15 November 2026

The existing trained models and original data are preserved. The baseline again
passed 40 tests; the current suite passes 48. HTTP QA passed 1,776 predictions
and 592 real explanations across all 592 offered profiles, plus expected invalid
requests. The existing run.ps1 workflow and production build pass.

- Original source cards/raw files still do not establish currency, taxes,
  passenger basis or booking journey type for selected cohorts. No INR relabeling
  or FX conversion was made.
- Four new distributions were inspected as audit-only data. Three share identical
  ordered 2019 common keys; others have unresolved semantics. Large Air India
  candidates explicitly declare synthetic generation. No new training data qualified.
- The 88/7 coverage gap is reproduced per airport: the broader network has no
  exact fitting cell above 17 observations. Lower thresholds lack adequate
  independent validation and were not adopted.
- A reliability correction withholds served intervals: the cabin final holdout
  is at lead days 41–50, outside the accepted 1–35 fitting range. Offline coverage
  remains available but cannot validate an accepted scenario's range.
- The seven clock-rounding failures are fixed without weakening real bounds.
- Browser access was denied at the Phase 2 audit. That restriction was later
  resolved; see the current authorized browser follow-up linked above.

Read [currency](reports/fare_currency_audit.md), [fare semantics](reports/fare_semantics_audit.md),
[airport eligibility](reports/airport_serving_eligibility_audit.md),
[new source research](reports/second_round_dataset_research.md),
[model reliability](reports/model_reliability_phase2.md) and
[QA](reports/browser_and_end_to_end_qa.md). No full model retraining or serving
expansion was justified. Next work should obtain documented real quotes and
independent query-day evaluation in the intended input domain.
<!-- SKYLENS_PHASE2_END -->
