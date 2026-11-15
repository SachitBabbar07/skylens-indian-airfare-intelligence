# API guide
Run ./run.ps1. The built frontend is at http://127.0.0.1:8000; generated API documentation is /docs.

GET /health reports artifact readiness (503 if incomplete). /model-info returns measured metadata. /supported-options?model_id=cabin_2023 returns eligible profiles and numeric bounds. /airports accepts query, model_id and supported_only; false exposes the full directory. /airlines returns eligible historical labels. /coverage distinguishes master/fare/serving evidence. /route-coverage filters eligible profiles by model_id, origin and destination. /feature-importance returns actual mean absolute SHAP.

POST /predict and /explain require model_id, origin, destination, airline, cabin_class, days_left, duration_minutes, stops, departure_hour and research_acknowledged=true. journey_type defaults to single_direction_record. Select a real combination and its bounds from /supported-options; do not assume every carrier serves every route/class. Network has zero eligible profiles and rejects ordinary scenarios. The prediction response includes estimate, source unit, null currency, unknown scope/passenger basis, support, warnings and an optional empirically evaluated interval. /explain returns baseline, thirteen contributions and additive error.

Extra fields, incorrect types, invalid ranges and unsupported routes/classes/carriers produce 422. Missing/corrupt models produce 503. Unexpected failures return safe 500 messages without stack traces. No travel_date, return_date or passenger_count is accepted because those targets are unsupported. Models load once; there is no retraining endpoint or fake fallback. Explicit local CORS origins are configurable through SKYLENS_CORS_ORIGINS.
<!-- SKYLENS_PHASE2_START -->
## Phase-two update

See PHASE2_FINDINGS.md for the current audit. Currency and full fare scope remain
unknown. The API now withholds intervals because the historical final holdout
does not overlap its serving ranges; it exposes /fare-semantics and explicit
airport serving statuses. Seven clock-rounding rejection cases were fixed with
microsecond-scale normalization. Tests and HTTP checks pass; browser QA remains
blocked by the saved permission policy. Existing models and training data were
preserved, and no wider serving or full retraining was justified.
<!-- SKYLENS_PHASE2_END -->
