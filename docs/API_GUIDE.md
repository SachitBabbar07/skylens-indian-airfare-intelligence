# API guide

Run `./run.ps1`. The built application is at [port 8000](http://127.0.0.1:8000); generated documentation is at [/docs](http://127.0.0.1:8000/docs).

## Flight search

- `GET /flights/airports` lists Indian IATA-coded airport records with name, city, state and a historical evidence flag. Directory entries describe known airports. Route support comes from a registered source.
- `GET /flights/capabilities` reports the travel options of registered sources, the domestic airline preference directory, and today's date in India. The legacy `indicative_estimates` field is always null.
- `POST /flights/estimate` accepts origin and destination IATA codes, `journey` (`one_way` or `round_trip`), `departure_date`, a round-trip `return_date`, `cabin`, optional `airline`, and `travellers` with adult, child and infant counts. Dates use `YYYY-MM-DD` in India Standard Time. The deprecated `/flights/search` alias returns the same summary.

### Estimate contract

| Fields | Meaning |
| --- | --- |
| `estimated_low`, `estimated_median`, `estimated_high` | Decimal strings in INR for the entire party and journey. A market sample of one to seven itineraries has a median and null bounds. An approved model point has equal low, median and high values. |
| `origin`, `destination`, `departure_date`, `return_date`, `journey_type`, `cabin_class`, `passenger_count` | The itinerary that was priced. |
| `currency`, `price_scope`, `taxes`, `fees` | Returned currency, whole-party basis, and whether taxes and fees are included, excluded or unknown. |
| `estimation_method`, `coverage_status`, `source_status` | Approved historical ML, market reference or unavailable, plus model coverage and each source's outcome. |
| `range_kind`, `stop_profile`, `market_statistics` | Point, limited sample, interquartile range, or unavailable. The market result reports stops in each direction, input and selected listing counts, observed price extrema, duration extrema per direction and the count outside the Tukey fences when a band is available. |
| `observation_count`, `disclaimer` | Number of distinct itineraries contributing to the market result and the applicable pricing limitations. |

A successful lookup with no usable observations returns HTTP 200, `estimation_method=unavailable` and null amounts. HTTP 422 identifies invalid input. HTTP 503 covers absent sources or provider authentication failure, 429 covers quotas and rate limits, 504 covers timeout, and 502 covers transport, certificate or malformed-response failures. Error bodies carry a sanitized message and code. The endpoint uses `Cache-Control: no-store`.

### How SkyLens calculates the estimate

1. A registered, independently evaluated customer model must accept the exact route, dates, airline preference, journey, cabin and passenger mix. Its result must carry an evaluation reference and a verified INR whole-party target with known tax and fee treatment. The two historical research artifacts do not qualify.
2. Outside approved coverage, the server requests exact-date domestic observations from Kiwi.com. It checks the returned currency, passenger counts, segments, carrier, cabin and times. The connector documents family-search prices for the entire party. Kiwi does not specify tax or fee inclusion in this response. [Provider documentation](https://www.kiwi.com/stories/kiwi-mcp-connector/)
3. SkyLens groups matching schedules and flight identities, checks elapsed duration against the timestamps, and takes one median of the distinct prices per itinerary within compatible monetary terms. It selects the fewest observed stops per direction independently of price. If no round-trip itinerary achieves both directional minima it abstains. Unknown tax or fee treatment can be grouped within one source. Among incompatible monetary groups for the selected stops, the largest group by distinct itineraries is used, with abstention on a tie unless a reviewed model has matching terms and stops.
4. One to seven itineraries yield only a median. Eight or more also yield Q1 and Q3 using linear interpolation at `(n - 1) × p`. Prices beyond Q1 − 1.5 IQR or Q3 + 1.5 IQR are counted as unusual and retain their weight. The band describes this provider sample, with no calibrated probability for a future booking price. [Evaluation and live diagnostic](../reports/market_accuracy_evaluation.md)
5. The bounded in-memory cache keeps eligible observations for up to 60 seconds for an identical request. A validated model takes priority, including when a recent market reference exists. Both values are retained in the internal decision and compared only under matching known terms. There are zero verified paired fare targets for fitting or testing ensemble weights. [Model and source audit](../reports/supervised_fare_status.md)

The market lookup needs no API key. Set `SKYLENS_KIWI_FARES_ENABLED=false` in the backend process environment for offline use. The numerical pipeline has no Groq dependency. Existing private credentials and historical generated ranges are unused. Booking links and individual offers are omitted from the estimate response.

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
