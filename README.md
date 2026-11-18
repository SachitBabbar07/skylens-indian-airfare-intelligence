# SkyLens · Indian Flight Search

SkyLens is a React and FastAPI application for Indian domestic flight search. On the Flights page, you can look up 165 Indian IATA-coded airports by city, airport name or code, swap airports and choose one-way or round-trip travel dates, travellers and cabin.

**Get estimate** returns one INR estimate for the selected trip and travelling party. SkyLens checks for an approved model with evaluated coverage first. For trips outside that coverage, it retrieves matching market observations from Kiwi.com, groups duplicate itineraries and calculates the median and middle 50% of the observed prices. A single itinerary yields one indicative amount. The source methodology appears below the estimate. [Fare API](docs/API_GUIDE.md#flight-search) · [Model and source audit](reports/supervised_fare_status.md)

## Research

The separate Research page keeps both frozen CatBoost models, historical route evidence, saved evaluation metrics, native SHAP explanations and quote intake. The source records lack documented currency, tax and fee inclusion, total versus base fare, passenger basis and booking type. Customer ML estimates remain disabled. Research diagnostics use **unverified model-output units**.

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

The app binds to loopback and loads existing model artifacts at startup. Use `npm --prefix frontend run dev -- --port 5173 --strictPort` for the optional development UI. [Flights](http://127.0.0.1:8000) · [Research](http://127.0.0.1:8000/research.html) · [API health](http://127.0.0.1:8000/health)

The offline CatBoost candidate trainer uses only verified quotes and a frozen chronological split. Its private evaluation compares model error with a route-and-airline median baseline. [Verified quote training](docs/QUOTE_COLLECTION_GUIDE.md)

A GitHub clone includes source, metadata and reports. Native models, raw/processed datasets, private quote evidence and backups stay outside Git. [Installation and artifact restoration](docs/INSTALLATION.md) distinguishes the submission workspace from a source-only clone.

## Verification

Run the Python suite with `PYTHONPATH=src`, `npm --prefix frontend test`, and `npm --prefix frontend run build`. Local checks cover the airport directory, journey validation, fare-source routing, malformed responses and price formatting. Offline fixtures exercise all four routing cases and the isolation of the numerical estimate from Groq. [Initial Flights verification](reports/flight_search_verification.md)

### v0.1.0 Research Edition

- **160 Python tests**, including artifact integrity and split leakage checks; **101 portable tests** also passed in a separate minimal environment.
- **15 frontend tests** and the production build passed. The live backend accepted 1,776 prediction checks and 592 SHAP checks across all 592 eligible profiles; 15 unsupported requests were rejected as expected.
- Desktop and mobile browser checks passed on the built application and the dev proxy, including an actual backend outage and retry recovery. Repository scans and npm/Python dependency audits passed. Hosted CI stays gated under the owner’s zero-spend decision.

[Final status](reports/phase6_system_status.md) · [Tests and performance](reports/phase6_test_report.md) · [Browser QA](reports/phase6_browser_qa.md) · [Data and model limitations](reports/phase6_data_model_limits.md) · [GitHub delivery](reports/github_delivery_report.md)

[API contract](docs/API_GUIDE.md) · [Quote intake](docs/QUOTE_COLLECTION_GUIDE.md) · [Dataset registry](data/metadata/dataset_registry.json) · [Source and license audit](reports/dataset_licensing_and_provenance.md)

Original code and documentation use the [MIT license](LICENSE). Third-party datasets, learned artifacts and dependencies retain their own terms. A source license does not establish a fare definition or permission to collect from an airline or booking site.
