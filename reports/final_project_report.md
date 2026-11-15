# Final project report
SkyLens is a local historical research application. A verified current INR total-fare predictor could not be established. Unknown currency, tax/passenger scope and booking journey type stay visible; source units are never labeled rupees.

Delivered: source discovery/acquisition, immutable originals and hashes, a 661-record airport master, honest mapping of fares to 88 historical airports, source-specific canonical research cohorts and exclusions, measured baselines/tuning, temporal/random/route/airport validation, native artifacts, real SHAP and empirical residual intervals, FastAPI, React, automated tests, reports/figures and learning guides.

| cohort | n | mae | rmse | r2 | median_absolute_error | mape_percent | p90_absolute_error | inference_ms_per_row | interval_coverage |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| network_2020 | 5445 | 2764.6631 | 4664.6755 | 0.4266 | 1583.1307 | 23.0764 | 6464.8287 | 0.0022 | 0.8516 |
| cabin_2023 | 88773 | 2339.7568 | 4376.3518 | 0.947 | 998.1895 | 13.7101 | 6142.7176 | 0.0013 | 0.8924 |

Not established: current verified INR totals, confirmed one-way booking fares, domestic returns/multi-city, First serving, reliable unseen routes/airports, compatible independent validation or broad network serving. All wider exact training cells have <=17 observations, below the unchanged minimum 50. Seven airports have eligible cabin research profiles. These limitations are enforced, not buried.

Forty automated tests and the TypeScript production build pass. Browser access was declined; mobile/interactive/visual browser QA remains unverified. No paid runtime dependency or credentials are needed. This is a working local research project with explicit data barriers, not a completed validated nationwide price service.


Additional executed checks: 592 advertised profiles passed real HTTP prediction with 0 failures; 2 compiled frontend assets and the HTML page returned HTTP 200. All 26 original file hashes match. Frozen-version acquisition was rerun successfully without raw overwrites. These checks do not replace the declined browser QA.


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
