# Phase 5 model validation

**No retraining or model selection occurred.** There is no new compatible verified target, so no new accuracy, stability or generalization result is claimed. Original native artifacts, scientific metadata, support and data are preserved in the [56-file baseline](../data/metadata/phase5/preservation_baseline.json), plus five protected pipeline/launch files.

| Frozen model | Test n | MAE | RMSE | R² |
| --- | --- | --- | --- | --- |
| cabin_2023 | 88773 | 2339.756824 | 4376.351779 | 0.947033389 |
| network_2020 | 5445 | 2764.663128 | 4664.675451 | 0.426647012 |

MAE/RMSE are unverified model-output units, not INR. R² is not accuracy. Research serving retains the same validated inputs, three cabin labels and exact-profile gates. Global importance and all thirteen native SHAP contributions remain available with their original interpretation limits.

Existing regression tests check actual split/fingerprint separation, native predictions and additive SHAP. Mirrors are excluded from independent validation; the source manifest and training/preparation code are unchanged. New-data leakage, subgroup stability and unseen-airport performance are not estimable from zero accepted new targets. Future independent chronological tuning/calibration/test windows must purge shared itineraries/segments and hold final targets untouched.

Intervals stay withheld: the historical holdout has no accepted-domain evidence. Conformal/residual/quantile methods cannot create missing representative calibration/test observations. No interval method was fit to synthetic or incompatible fares. Executed test/build/browser results are in [final findings](phase5_final_findings.md).
