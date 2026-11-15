# Model reliability review

Saved final-test metrics were recomputed from every saved actual/prediction pair.
They match both metadata files. A fresh native prediction sample of 100 real
test rows per model matches the saved predictions. All original data/model hashes
and all six split-pair quote/fingerprint disjointness checks pass. See
data/metadata/phase2/baseline_reconciliation.json.

Existing random, route, airport and temporal results are preserved. Per-airport,
route, carrier, class, journey label, booking window, price and duration subgroup
errors remain in the original subgroup CSVs. Different protocols/250-tree stress
fits are not falsely compared as the same final model.

| cohort | protocol | n | mae | rmse |
| --- | --- | --- | --- | --- |
| network_2020 | random_quote_group_holdout | 1406 | 2375.57 | 4163.643 |
| network_2020 | route_holdout_known_airports | 2493 | 2428.658 | 4219.534 |
| network_2020 | route_holdout_known_airports | 2226 | 2482.231 | 4304.998 |
| network_2020 | route_holdout_known_airports | 2276 | 2424.167 | 4026.074 |
| network_2020 | unseen_airport_holdout | 1022 | 2350.393 | 3679.838 |
| network_2020 | unseen_airport_holdout | 82 | 3584.723 | 6242.141 |
| cabin_2023 | random_quote_group_holdout | 62419 | 3489.794 | 6220.186 |
| cabin_2023 | route_holdout_known_airports | 113302 | 4489.171 | 7281.677 |
| cabin_2023 | route_holdout_known_airports | 101399 | 4404.153 | 7087.925 |
| cabin_2023 | route_holdout_known_airports | 97267 | 4385.049 | 7206.561 |
| cabin_2023 | unseen_airport_holdout | 113186 | 4996.453 | 8437.126 |
| cabin_2023 | unseen_airport_holdout | 112290 | 4415.511 | 6920.514 |
| cabin_2023 | unseen_airport_holdout | 101082 | 4603.372 | 7320.109 |
| cabin_2023 | unseen_airport_holdout | 82632 | 4262.465 | 6899.639 |
| cabin_2023 | unseen_airport_holdout | 78145 | 4125.74 | 6649.172 |
| cabin_2023 | unseen_airport_holdout | 75984 | 5503.769 | 8763.154 |
| cabin_2023 | unseen_airport_holdout | 60617 | 5675.679 | 8572.045 |

## Explicit generalization categories

1. Known airports and observed route: the retained cabin research product; still
   unverified target semantics and no independent final-test rows inside its
   numeric serving domain.
2. Known airports, unseen directional route: existing route-grouped diagnostics
   have errors around 4,385–4,489 cabin source units. Reverse routes may still
   exist in training; this is not an unseen undirected airport pair guarantee.
3. One unseen endpoint: existing leave-airport diagnostics plus the new two-held
   airport experiment below.
4. Both endpoints unseen: now explicitly separated in a development-only
   two-airport holdout.
5. Insufficient evidence: sparse/unknown combinations remain blocked. The network
   model has no eligible exact serving profile.

The new experiment holds out the two most frequent airports based on observation
counts only, removes every row touching either from fitting, and separately
evaluates one versus both unseen endpoints. It uses 250-tree diagnostic models,
the unchanged source targets, and only train/validation development rows.

| cohort | category | held_airports | n | mae | rmse |
| --- | --- | --- | --- | --- | --- |
| network_2020 | one_unseen_endpoint | BOM/BLR | 1890 | 2372.313 | 3777.706 |
| network_2020 | both_endpoints_unseen | BOM/BLR | 25 | 1998.985 | 2672.307 |
| cabin_2023 | one_unseen_endpoint | BOM/DEL | 175362 | 4679.331 | 7772.345 |
| cabin_2023 | both_endpoints_unseen | BOM/DEL | 25057 | 5045.975 | 8130.792 |

Network has only 25 both-unseen rows for its chosen pair, so that low sample error
cannot establish reliability. Cabin's both-unseen error is about 5,046 source
units, substantially worse than familiar-domain diagnostics. Neither airport-pair
experiment represents all unseen airports. No new-route or unseen-airport serving
is enabled.

## Serving-domain correction

| cohort | fitting_lead_range | calibration_lead_range | test_lead_range | test_rows | test_rows_inside_current_serving_domain | eligible_cells | largest_fitting_profile |
| --- | --- | --- | --- | --- | --- | --- | --- |
| cabin_2023 | [1, 35] | [36, 40] | [41, 50] | 88773 | 0 | 592 | 1714 |
| network_2020 | [0, 28] | [0, 28] | [0, 28] | 5445 | 0 | 0 | 17 |

Cabin fitting leads are 1–35 days, calibration 36–40 and test 41–50. All 88,773
final-test rows are outside the API's accepted support ranges. The old 89.24%
offline interval coverage is correctly measured, but **does not validate an
interval for an accepted user request**. Aggregate coverage and a route row count
were insufficient gates. The API now withholds intervals and explains why;
offline artifacts/metrics and point research estimates are preserved.

No full retraining or model replacement is justified. Priority is documented
quote semantics and fresh independent query-day observations, followed by
calibration/evaluation within the intended serving domain. Larger datasets,
geographic features and lower row thresholds cannot substitute for those checks.
