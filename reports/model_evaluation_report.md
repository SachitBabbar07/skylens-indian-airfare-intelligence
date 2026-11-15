# Model evaluation
| cohort | n | mae | rmse | r2 | median_absolute_error | mape_percent | p90_absolute_error | inference_ms_per_row | interval_coverage |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| network_2020 | 5445 | 2764.6631 | 4664.6755 | 0.4266 | 1583.1307 | 23.0764 | 6464.8287 | 0.0022 | 0.8516 |
| cabin_2023 | 88773 | 2339.7568 | 4376.3518 | 0.947 | 998.1895 | 13.7101 | 6142.7176 | 0.0013 | 0.8924 |

Error units are source fare units, not verified rupees. MAE averages absolute misses; RMSE emphasizes large errors; median absolute error shows a typical miss; MAPE applies only to positive prices; p90 absolute error exposes the error tail. R² is explained variance under this protocol, not accuracy.

Mean, median, Ridge, a depth-limited decision tree and three CatBoost settings share identical selection partitions. The fixed three-setting search is small and reproducible, not exhaustive optimization. model_comparison.csv records every validation score, training time and inference time. CatBoost is selected by validation MAE with a stop if a simpler baseline is materially better; native additive explanation availability also favors operational simplicity. Final fits use train+validation only. Saved metadata includes parameters, seed 42, training date, hashes and schema.

Network: earliest collection day trains; middle-day quote groups are deterministically split for validation/calibration; latest collection day is the final holdout. Cabin: first 60% departure days train, next 10% validation, next 10% calibration and last 20% final test, all from one collection snapshot. This is not future booking-day validation.

Development-only random quote-group, route and unseen-airport tests are stored separately. Stress models cap tree count at 250, explicitly differing from final 400/550-tree fits. They diagnose gaps and never authorize unseen-airport serving. Class, journey, airline, airport, route, booking-window, price-range, stops and duration errors are in COHORT_subgroup_metrics.csv.

The historical interval uses a finite-sample 90% absolute-residual quantile from calibration data, then truncates the lower bound at zero for positive fares. Temporal dependence means conformal exchangeability is not established; no distribution-free/future-price guarantee is claimed. Actual test coverage: network 85.16%; cabin 89.24%. The API requires at least 30 tested route observations and aggregate coverage >=85% to expose a historical range. This heuristic does not establish conditional calibration. Never call the range a confidence interval or promise 90% coverage for each route/class.


## Additional cabin architecture diagnostic
| architecture | class | n | mae | rmse |
| --- | --- | --- | --- | --- |
| pooled | Business | 12788 | 5340.21 | 8557.315 |
| class_specific | Business | 12788 | 4751.384 | 7957.138 |
| pooled | Economy | 25231 | 1284.659 | 2103.226 |
| class_specific | Economy | 25231 | 1247.582 | 2067.501 |
| pooled | Premium Economy | 6661 | 1672.229 | 3044.729 |
| class_specific | Premium Economy | 6661 | 1339.922 | 2733.472 |
These are post-hoc development-only results. The frozen pooled artifact and its final-test results remain unchanged. Separate class models are a promising follow-up requiring a fresh untouched evaluation before promotion. Reproduce with `$env:PYTHONPATH = "src"` then `.venv\Scripts\python.exe scripts\compare_cabins.py`.
<!-- SKYLENS_PHASE2_START -->
## Phase-two correction — 15 November 2026

The original report above records phase-one results. Phase-two inspection
confirmed its numeric metrics but found zero cabin final-test rows inside the
current numeric serving domain (fit lead days 1–35, test 41–50). The old aggregate
interval gate is no longer used: API intervals are withheld. Seven clock-float
boundary rejections were fixed; genuine out-of-range values remain rejected.
Training data/model artifacts, the 50-row rule and the 88-observed/7-research/
0-production airport counts remain unchanged. See model_reliability_phase2.md,
airport_serving_eligibility_audit.md and browser_and_end_to_end_qa.md.
<!-- SKYLENS_PHASE2_END -->
