# Final data and model limitations — 16 November 2026

**No verified all-in INR target is available.** The original collectors did not establish currency, tax/fee inclusion, total versus base fare, passenger basis or genuine booking type. Historical single-direction records do not establish a one-way booking. The [original-source re-audit](price_target_reaudit_20261115.md) and [Phase 5 comparisons](phase5_dataset_comparison.csv) remain the evidence for this decision; Phase 6 did not reopen dataset search.

| Frozen model | Test rows | MAE | RMSE | R² | Release use |
| --- | ---: | ---: | ---: | ---: | --- |
| Cabin 2023 | 88,773 | 2,339.76 | 4,376.35 | 0.9470 | Exact eligible historical profiles, Economy, Business, Premium Economy |
| Network 2020 | 5,445 | 2,764.66 | 4,664.68 | 0.4266 | Offline metrics; no profiles meeting 50 fitting observations |

MAE, RMSE, model values and SHAP contributions use unverified units. R² describes explained variance in the historical holdout, not customer accuracy. First Class appears in historical listings but is excluded from eligible research. Routes and carriers are historical. No current schedule, verified fare, round trip or multi-city offer is supported. Offline residual coverage does not validate the accepted numeric domain, so served intervals stay null.

The registered cabin source is a single collection day; the broader network source spans three observed days, and the subsequent challenge is excluded from fitting. No new verified quotes, usable source grants, training runs or eligibility changes occurred. Model binaries, original data and scientific artifacts match the [frozen manifest](../data/metadata/phase5/preservation_baseline.json). Future customer use requires documented target semantics and reuse rights, sufficient independent observations and evaluation in the intended serving scope.
