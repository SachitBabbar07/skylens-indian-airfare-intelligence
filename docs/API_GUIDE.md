# API guide

Run `./run.ps1`. The built application is at [port 8000](http://127.0.0.1:8000); generated documentation is at [/docs](http://127.0.0.1:8000/docs).

## Flight search

- `GET /flights/airports` lists Indian IATA-coded airport records with name, city, state and a historical evidence flag. Directory entries describe known airports. Route support comes from a registered source.
- `GET /flights/capabilities` reports the travel options for each registered source and today's date in India. Both `live_quotes` and `ml_estimates` are currently null.
- `POST /flights/search` accepts origin and destination IATA codes, `journey` (`one_way` or `round_trip`), `departure_date`, `return_date` for round trips, `cabin` and `travellers` (`adults`, `children`, `infants`). Dates use `YYYY-MM-DD` and are validated in India Standard Time.

`results` contains `live_quote` or `ml_estimate` records. Each price has a decimal amount, source currency, `party_total` basis, tax and fee status, cabin, exact travellers, source name and retrieval time. Live quotes also require available itineraries with matching airports and dates, named airlines and time-zone-aware times. `results: []` means a supported source completed the search and returned zero results. The API sends `Cache-Control: no-store` with fare responses.

Application errors supply `detail.code` and `detail.message`. Status 422 covers invalid or unsupported input. Status 503 reports missing provider or authentication failure. Status 429 reports quota or rate limits, 504 reports timeouts, and 502 reports provider failures or incomplete responses. Provider authentication occurs on the backend. The published app has neither a live provider adapter nor an approved customer fare model.

## Customer ML capability

`GET /capabilities` reports `fare_estimation.available=false`, null currency, no approved model and the missing evidence. `POST /fare-estimate` returns **503** with:

> Fare prediction is temporarily unavailable because the training data's price definition has not yet been verified.

Former generic `POST /predict` and `/explain` also return 503. This deliberate contract change prevents cached price-card clients from obtaining new research outputs. Migrate research consumers to the explicit paths below. No environment variable, request flag or INR metadata label enables customer estimation. Documented target semantics and independent evaluation for the intended scope are required for a reviewed future release.

## Acknowledged research

`POST /research/predict` and `/research/explain` require `model_id`, `origin`, `destination`, `airline`, `cabin_class`, `days_left`, `duration_minutes`, `stops`, `departure_hour` and `research_acknowledged=true`. `journey_type` defaults to `single_direction_record`; this does not establish a genuine one-way booking. Obtain an exact combination and its bounds from `/supported-options`. Network has zero eligible profiles and rejects ordinary scenarios.

The compatibility field `estimate` means **raw numerical model output**, not a fare estimate, ticket price, booking quote or verified INR amount. The compatibility unit code remains `source fare units`; `unit_verification=unverified`, `currency=null`, `research_only=true` and `output_kind=unverified_research_model_output` identify its status. The UI uses **unverified model-output units**. There is no currency conversion. Scope and passenger basis remain unknown. Intervals are always null with `withheld_unvalidated_serving_domain` because the holdout does not validate accepted input ranges.

Explanations return raw output, baseline, thirteen native SHAP contributions and additive error in the same unverified units, not rupee increases or savings. Response contracts reject monetary relabelling, customer promotion and served intervals.

Extra fields, incorrect types, invalid ranges and unsupported profiles produce 422. Missing/corrupt models produce 503; unexpected failures return safe 500 messages. No travel date, return date, passenger count, currency or conversion rate is accepted. Models load once; requests never train and errors never return fabricated output.

## Metadata and diagnostics

`GET /acquisition/status` returns the dated Phase 5 acquisition review, separate verified one-way/return counts and unchanged customer/training-disabled flags. Missing/unsafe review metadata returns 503. `/acquisition/template.csv` downloads a header-only manual-intake CSV; `/acquisition/schema` exposes quote/source-grant schemas. These are read-only endpoints, with no upload, automatic ingestion or training. Optional license/reuse labels do not grant rights; a supplied booking lead must match the actual observation and travel dates. See the [acquisition decision](../reports/phase5_acquisition_decision.md).

`GET /health` reports artifact readiness (503 if incomplete), separately from production-predictor unavailability. `/model-info` exposes frozen research metadata. `/supported-options?model_id=cabin_2023` exposes profiles and bounds. `/airports` accepts `query`, `model_id` and `supported_only`; false exposes the full directory. `/airlines` exposes historical labels. `/coverage` distinguishes master, observed and eligible research evidence. `/route-coverage` filters profiles. `/fare-semantics` exposes the original audit. `/feature-importance` exposes actual mean absolute SHAP in unverified units.

`GET /research/evidence` serves the frozen dataset summaries and historical route counts by direction, cohort and cabin. It contains no prices and remains available independently of loaded models. The distinct route count is 720 across all three cohorts; the external challenge was not used in fitting. Directory records with a missing model cannot be marked eligible. Larger responses use gzip when the client accepts it. Validation failures report the field and reason without echoing the request body.

CORS uses configured local origins in `SKYLENS_CORS_ORIGINS`. Vite proxies these endpoints, `/flights`, `/research/`, `/capabilities`, `/fare-estimate`, `/docs` and `/openapi.json`. The Research page is served at `/research.html`. [Source re-audit](../reports/price_target_reaudit_20261115.md) · [Product correction](../reports/product_correction_20261115.md)
