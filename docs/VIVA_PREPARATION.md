# Viva preparation
**Problem statement:** Public airfare data are uneven, and prices change with itinerary conditions. I built a traceable historical research system and tested which claims its data can support.

**Why not claim all airports?** The master has 661 airfield records, selected fares map to 88 airports, and only seven have eligible cabin research profiles. Zero qualify for verified current INR totals. Airport metadata is not fare evidence.

**Why these data?** The 2023 source offers cabin/booking fields; PromptCloud offers wider geography. Actual files, licenses, duplicate lineage and price definitions determine selection. Raw/cleaned copies are not independent observations. The Goibibo derivative cannot validate a later period.

**Why no live quote or round trip?** Tax inclusion, passenger basis, currency fields and booking types are undocumented in selected sources. There is no qualified domestic return-price/return-date dataset. Summing two one-way-looking rows would invent a return booking.

**What was cleaned?** Dates and durations were parsed; reviewed city aliases were joined; international/unmapped itineraries were excluded with reasons; duplicates were removed; valid expensive fares stayed. First has only 144 rows and is not trained/offered.

**Features:** Endpoints, carrier, class, stops, duration, lead time, departure hour and geography. They are scenario inputs or target-independent metadata; target values and post-flight outcomes are excluded.

**Why CatBoost?** It performed well against tested baselines on the same validation partitions and supports native additive explanations. Three configurations were tried, not every algorithm. Saved comparison CSVs show the alternatives.

**How is leakage prevented?** Distinct quote/fingerprint groups across train, validation, calibration and final test; fold-specific preprocessing; no target-derived features; no concatenated mirrors; no test tuning.

**Actual results:** Cabin MAE 2339.76, RMSE 4376.35, R² 0.9470. Network MAE 2764.66, RMSE 4664.68, R² 0.4266. These are source fare units, not rupees. R² is not percent accuracy.

**Validation limits:** Random groups test familiar distributions; route holdouts and airport holdouts test different gaps. Cabin departure-day chronology is only one booking snapshot, not future booking-day evidence. Geographic stress fits cap trees at 250 and do not enable unseen-airport serving.

**SHAP:** Baseline plus input contributions equals the fitted prediction. Positive raises that output, negative lowers it. Association is not causation.

**App architecture:** React retrieves metadata and sends validated scenarios to FastAPI. FastAPI loads hashed native artifacts and returns real model and SHAP outputs. It never retrains per request or fills failures with samples.

**Improvements:** Legitimately licensed quotes with documented INR/taxes/passengers/journey type, repeated query dates, more joint route evidence, compatible independent validation and current service verification. Browser visual/interactive QA also remains unfinished because permission was declined.
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
