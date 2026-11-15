# Data audit
| cohort | input | retained | excluded | origins | destinations | routes |
| --- | --- | --- | --- | --- | --- | --- |
| cabin_2023 | 452088 | 445366 | 6722 | 7 | 7 | 42 |
| network_2020 | 30024 | 14877 | 15147 | 63 | 82 | 679 |
| network_external_2020 | 30000 | 22735 | 7265 | 66 | 80 | 685 |

Actual per-file schemas, dtypes, missing values, duplicates, hashes and samples are in data/metadata/file_profiles.json. Per-row exclusions in data/interim reconcile input = retained + excluded. International/unmapped endpoints/layovers are rejected; valid missing layover slots are not invented. Exact canonical duplicates are removed before splitting. Valid expensive fares remain. First's 144 rows stay in audit data but are excluded from training.

The 2023 raw/cleaned pair agrees on all recorded fares, departure dates and lead times. Its sole collection day prevents identifying independent booking-date and seasonal effects. Source 2+-stop remains a bucket represented as 2, not a claim of exactly two stops. Network carrier combinations retain original strings. Network cabin remains Unspecified.

All selected currencies, passenger bases and tax scopes remain unknown; normalized INR is entirely missing. Single-direction records do not establish genuine one-way booking settings. No return date is fabricated. Reviewed city aliases join unique nonempty Indian IATA codes, without fuzzy nearest-airport matching. Historical Goa maps to GOI and pre-2023 Rajkot to RAJ; no historical RAJ fare is silently moved to HSR. These mappings do not confirm current operations.
