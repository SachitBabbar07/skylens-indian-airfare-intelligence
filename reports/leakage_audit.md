# Leakage audit
The raw and cleaned files are representations, never stacked. The Goibibo derivative is excluded; source_overlap_audit.json contains the measured alignment. Canonical duplicates are removed before splits. Quote keys use endpoints, carrier/flight, class, travel date, departure hour, duration and stops, excluding price and collection timestamp. Earlier appearances of quotes present in later partitions are purged.

| cohort | train | validation | calibration | test | purged_earlier_quotes |
| --- | --- | --- | --- | --- | --- |
| network_2020 | 4750 | 2278 | 2354 | 5445 | 50 |
| cabin_2023 | 267288 | 44680 | 44481 | 88773 | 0 |

All six partition pairs pass quote-group and exact-fingerprint disjointness assertions. Automated tests repeat these checks. The split manifests preserve source IDs and dates. Encoders/scalers live inside each training pipeline. Native CatBoost categorical statistics are fit only on the training portion. Geography is target-independent; target prices, IDs, source labels and post-flight outcomes are not features.

The final test does not choose parameters; calibration does not fit the model. Random, route and unseen-airport stress tests use development data only. Airport holdouts remove all rows touching the held airport in either direction. Route holdouts evaluate only endpoints still present in training. Native SHAP on test observations is post-selection analysis, not feature tuning.

Residual limitation: all cabin observations were collected on one day, linking lead time and travel date. Repeated flight numbers across different departure dates remain because familiar services are part of the intended research scenario. This does not establish unseen-flight generalization. The later PromptCloud challenge removes exact fingerprint overlap, but shared collector and unknown target definitions prevent a fully independent validation claim.
