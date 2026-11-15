# Model guide
Regression estimates a number from inputs. Mean/median baselines ignore inputs and set a reference error. Ridge learns a regularized weighted combination after training-only encoding/scaling. A decision tree learns conditional branches. CatBoost combines many trees and handles categorical data with training-only statistics.

Seven configurations per source share validation partitions. Three fixed tree settings form a small reproducible hyperparameter search, not exhaustive optimization. Validation MAE selects a tree model, with a stop if a simpler baseline is materially better. Native additive explanations are also operationally useful. Final settings: {"network_2020": {"iterations": 400, "depth": 8, "learning_rate": 0.06, "l2_leaf_reg": 5}, "cabin_2023": {"iterations": 550, "depth": 7, "learning_rate": 0.07, "l2_leaf_reg": 7}}.

MAE is the average size of a miss. RMSE gives large misses more weight. Median absolute error describes a typical case. MAPE uses positive target values and is a percentage, while R² measures explained variance under this experiment; it is not accuracy. All absolute errors here use source units, not verified rupees.

The final holdout is not used to choose parameters. The network tests the latest collection day, while the cabin model tests later departure dates from one snapshot. Random groups, unseen routes and unseen airports answer distinct questions; those stress fits use development data and cap iterations at 250, unlike the final models. They never authorize new-airport serving.

Calibration measures held-out absolute residuals. Nominal 90% is a target: measured coverage is 85.16% for network and 89.24% for cabin. Dependence/temporal shift means exchangeability is not established, so the usual conformal coverage guarantee cannot be claimed. These historical residual ranges are not confidence intervals or future-price promises.


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
## Phase-two update

See PHASE2_FINDINGS.md for the current audit. Currency and full fare scope remain
unknown. The API now withholds intervals because the historical final holdout
does not overlap its serving ranges; it exposes /fare-semantics and explicit
airport serving statuses. Seven clock-rounding rejection cases were fixed with
microsecond-scale normalization. Tests and HTTP checks pass; browser QA remains
blocked by the saved permission policy. Existing models and training data were
preserved, and no wider serving or full retraining was justified.
<!-- SKYLENS_PHASE2_END -->
