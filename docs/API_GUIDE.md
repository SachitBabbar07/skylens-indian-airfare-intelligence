# API guide

Run `./run.ps1`. The built application is at [port 8000](http://127.0.0.1:8000); generated documentation is at [/docs](http://127.0.0.1:8000/docs).

## Customer capability is unavailable

`GET /capabilities` reports `fare_estimation.available=false`, null currency, no approved model and the missing evidence. `POST /fare-estimate` returns **503** with:

> Fare prediction is temporarily unavailable because the training data's price definition has not yet been verified.

Former generic `POST /predict` and `/explain` also return 503. This deliberate contract change prevents cached price-card clients from obtaining new research outputs. Migrate research consumers to the explicit paths below. No environment variable, request flag or INR metadata label enables customer estimation. Documented target semantics and independent evaluation for the intended scope are required for a reviewed future release.

## Acknowledged research

`POST /research/predict` and `/research/explain` require `model_id`, `origin`, `destination`, `airline`, `cabin_class`, `days_left`, `duration_minutes`, `stops`, `departure_hour` and `research_acknowledged=true`. `journey_type` defaults to `single_direction_record`; this does not establish a genuine one-way booking. Obtain an exact combination and its bounds from `/supported-options`. Network has zero eligible profiles and rejects ordinary scenarios.

The compatibility field `estimate` means **raw numerical model output**, not a fare estimate, ticket price, booking quote or verified INR amount. The compatibility unit code remains `source fare units`; `unit_verification=unverified`, `currency=null`, `research_only=true` and `output_kind=unverified_research_model_output` identify its status. The UI uses **unverified model-output units**. There is no currency conversion. Scope and passenger basis remain unknown. Intervals are always null with `withheld_unvalidated_serving_domain` because the holdout does not validate accepted input ranges.

Explanations return raw output, baseline, thirteen native SHAP contributions and additive error in the same unverified units, not rupee increases or savings. Response contracts reject monetary relabelling, customer promotion and served intervals.

Extra fields, incorrect types, invalid ranges and unsupported profiles produce 422. Missing/corrupt models produce 503; unexpected failures return safe 500 messages. No travel date, return date, passenger count, currency or conversion rate is accepted. Models load once; requests never train and errors never return fabricated output.

## Metadata and diagnostics

`GET /health` reports artifact readiness (503 if incomplete), separately from production-predictor unavailability. `/model-info` exposes frozen research metadata. `/supported-options?model_id=cabin_2023` exposes profiles and bounds. `/airports` accepts `query`, `model_id` and `supported_only`; false exposes the full directory. `/airlines` exposes historical labels. `/coverage` distinguishes master, observed and eligible research evidence. `/route-coverage` filters profiles. `/fare-semantics` exposes the original audit. `/feature-importance` exposes actual mean absolute SHAP in unverified units.

CORS uses configured local origins in `SKYLENS_CORS_ORIGINS`. Vite proxies these endpoints, `/research`, `/capabilities`, `/fare-estimate`, `/docs` and `/openapi.json`. See the [source re-audit](../reports/price_target_reaudit_20261115.md) and [product correction](../reports/product_correction_20261115.md).
