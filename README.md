# SkyLens · Research Edition

SkyLens is a local research application for Indian domestic aviation. It connects a FastAPI backend, a React interface and two frozen CatBoost models to searchable airport and route evidence, saved evaluation metrics and native SHAP explanations.

**Customer fare prediction is unavailable.** Source records do not establish currency, mandatory taxes and fees, total versus base fare, passenger basis or genuine booking type. Research outputs use **unverified model-output units**. SkyLens does not format them as INR or show them as quotes.

| Evidence | Coverage |
| --- | ---: |
| Indian airport and airfield directory | 661 records, 165 with IATA codes |
| Historical listing evidence | 88 airport endpoints, 720 directional routes |
| Eligible cabin-model research | 7 airports, 42 directional routes, 592 exact profiles |
| Verified customer fare prediction | 0 airports, 0 approved models |

Coverage distinguishes historical listings from exact model support. Filter routes by IATA, cohort or cabin; filter eligible profiles by route, cabin, carrier and stops; then open a profile in Research tools. Methodology shows saved test metrics. The overview provides the empty quote CSV, schema and existing offline validation workflow. The network model has saved evaluation results but no profiles that meet the serving gate.

## Run locally

On Windows with Python 3.12, Node 22 or newer and [uv](https://docs.astral.sh/uv/), from the existing workspace:

```powershell
Set-Location D:\SkyLens
.\setup.ps1   # First install or after dependency changes; stop running SkyLens servers first.
.\run.ps1
```

Open [SkyLens](http://127.0.0.1:8000) or [API health](http://127.0.0.1:8000/health). A separate development UI is optional: `npm --prefix frontend run dev -- --port 5173 --strictPort`. No account, API key, paid dependency or live fare service is required to launch. The app binds to loopback and loads the models without fitting them.

A GitHub clone includes source, metadata and reports. Native models, raw/processed datasets, private quote evidence and backups stay outside Git. [Installation and artifact restoration](docs/INSTALLATION.md) distinguishes the submission workspace from a source-only clone.

## Release verification

- **160 Python tests**, including artifact integrity and split leakage checks; **101 portable tests** also passed in a separate minimal environment.
- **15 frontend tests** and the production build passed. The live backend accepted 1,776 prediction checks and 592 SHAP checks across all 592 eligible profiles; 15 unsupported requests were rejected as expected.
- Desktop and mobile browser checks passed on the built application and the dev proxy, including an actual backend outage and retry recovery. Repository scans and npm/Python dependency audits passed. Hosted CI stays gated under the owner’s zero-spend decision.

[Final status](reports/phase6_system_status.md) · [Tests and performance](reports/phase6_test_report.md) · [Browser QA](reports/phase6_browser_qa.md) · [Data and model limitations](reports/phase6_data_model_limits.md) · [GitHub delivery](reports/github_delivery_report.md)

[API contract](docs/API_GUIDE.md) · [Quote intake](docs/QUOTE_COLLECTION_GUIDE.md) · [Dataset registry](data/metadata/dataset_registry.json) · [Source and license audit](reports/dataset_licensing_and_provenance.md)

Original code and documentation use the [MIT license](LICENSE). Third-party datasets, learned artifacts and dependencies retain their own terms. A source license does not establish a fare definition or permission to collect from an airline or booking site.
