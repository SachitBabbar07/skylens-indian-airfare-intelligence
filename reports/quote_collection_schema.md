# Genuine quote schema and quality gates

The executable schema is [quotes.py](../src/skylens/quotes.py); generated machine-readable definitions are [quote_schema.json](../config/quote_schema.json). The [CSV template](../config/quote_template.csv) contains a header and **zero observations**. Blank CSV cells become unknown/null or a documented schema default; raw bytes are always retained after the permission gate.

| Field group | Meaning |
| --- | --- |
| Identity/provenance | `quote_id` is a unique local snapshot identifier; `source_id`, source name/public HTTPS URL, optional source record ID, acquisition method and live/historical/test/unknown environment remain explicit. Strip session/auth/query tokens from URLs. |
| Collection | `collected_at_utc` must have zero UTC offset. Optional local timestamp must describe the same instant at +05:30. Software derives collection day in Asia/Kolkata; quote time is not file modification time. |
| Journey | Actual IATA origin/destination, departure/return dates and one_way/round_trip/multi_city/unknown. A return needs both connected outbound and inbound segments in the same booking evidence. Never add unrelated one-way totals. |
| Itinerary | Segment list with origin, destination, offset-aware departure/arrival, marketing/optional operating carrier, flight number, cabin and outbound/inbound leg. Segment chronology/endpoints/date agreement are validated. Stops means total connections across supplied legs; one-way duration is elapsed segment time including connections. Original time strings remain in raw CSV/evidence. |
| Product | Airline, operating airline where supplied, cabin, fare family, baggage and refundability. Unknown operating carrier/fare family stays null. Mixed-cabin segments remain research-only under the initial homogeneous-cabin target. |
| Passengers | Count and JSON composition (`adults`, `children`, `infants`) must agree. No names, DOBs, email, passport, PNR, account ID or payment data. Initial verified target restricts to exactly `{"adults":1}`. Larger-party observations can be retained for research if licensed, without inventing a per-adult division. |
| Money | Decimal original currency, base, taxes, fees, displayed total, total scope, tax/fee inclusion statuses and optional explicitly comparable per-passenger total. Components, if supplied, must have the same currency/scope as the displayed total. Included complete components must reconcile within 0.01. Zero is a stated amount, not an unknown. No exchange-rate conversion. |
| Availability | selectable/unavailable/indicative/unknown. A quote is a historical offer at the collection instant, not a purchase, confirmed seat, guarantee or payment instruction. |
| Evidence/review | Private evidence relative path + SHA-256, source terms URL, reviewer ID and timestamp, and semantic-field → evidence-location JSON. Original quoted labels/strings may be supplied in `original_values`; immutable raw bytes remain authoritative. |

## Separate gates

1. **Permission:** without collection, storage and no-cost authorization, the whole batch is rejected before raw/evidence retention. Matching domain/method/terms, time window, permission hash, retention and daily limits are enforced. A permission reviewer must first check actual source terms. No automatic collector is provided.
2. **Schema:** malformed authorized travel dates/amounts/JSON, extra fields, contradictory trips/passengers/components/segments or future timestamps enter a private quarantine record with row number and invalid field names. An unparseable collection timestamp cannot be bound to the source permission period, so the batch is rejected before retention. Other authorized original batches are retained for correction.
3. **Verified target candidate:** explicit INR, all taxes and mandatory fees included, single adult, selectable itinerary, one-way or actual connected round-trip, uniform known cabin/carrier/flight segments, reviewed Indian IATA endpoints and evidence locations for every mandatory semantic field. Evidence file/hash and human review are required. Missing semantics or ML permission yields research-only status. No guessed INR or passenger basis.
4. **Experiment admission:** conflict resolution, independent sampling, target compatibility, grouped temporal splits and a new experiment review are still required. `verified_target` is an intake label, not automatic training or model eligibility. The legacy cohorts and these new INR targets must remain separate.

## History, conflicts and failure handling

Private `data/quotes/` holds content-addressed raw CSV, permission snapshots, evidence blobs, immutable batches, replay receipts and error-type-only failure logs. A store lock prevents overlapping CLI writers. Files are created exclusively; a changed existing immutable file is rejected. Reads verify batch/raw/permission hashes; target summaries recheck retained evidence hashes and retention expiry. A crash may leave an unreferenced blob; retry is safe and never overwrites it. Remove a stale lock only after confirming its owner has stopped.

Exact raw/config replay is idempotent. Same source/itinerary/collection instant with identical meaning is a duplicate even if it has a new quote ID. Conflicting versions of an ID or snapshot are all excluded until a documented human resolution; neither wins by upload order. Repeated times/days remain snapshots, with distinct itinerary/day counts. A malformed reuse of an existing ID also blocks that ID. Raw history is never silently edited to resolve a dispute.

Software checks consistency and binds files; it cannot prove a screenshot is authentic, that the reviewer read the terms, or that an airline grants rights. Evidence review is a real human responsibility. Retention deadlines require timely human deletion of licensed private payloads before expiry; immutability is not permission to retain expired material. No actual licensed payload currently exists in this store.
