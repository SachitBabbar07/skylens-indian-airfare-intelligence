# Explainability
Native CatBoost SHAP comes from fitted models, not handwritten pricing rules. Global importance averages absolute contributions over a fixed seed-42 sample of up to 400 final-test rows. Validation permutation importance shuffles one feature at a time using the selection-fit model; correlated coordinates/distance mean it is not an independent causal ranking.

Saved real cabin example: prediction 12483.3436, baseline 22917.8513, in source units.

| feature | input | contribution |
| --- | --- | --- |
| origin | BLR | -49.7187 |
| destination | BOM | 350.2599 |
| airline | Vistara | 1966.7284 |
| cabin_class | Economy | -14109.2077 |
| stops | 1 | 363.7792 |
| duration_minutes | 455 | 1442.3637 |
| days_left | 41 | -1894.5355 |
| departure_hour | 11.5 | 1005.0424 |
| distance_km | 834.1626287828708 | 228.7102 |
| origin_lat | 13.1979 | 196.1685 |
| origin_lon | 77.706299 | -245.811 |
| destination_lat | 19.088699 | 532.2997 |
| destination_lon | 72.867897 | -220.5868 |

Baseline plus all contributions reproduces the model output within 1e-6; automated tests repeat additivity for both fitted models. Positive contributions raise the output relative to the baseline, negative ones lower it. Neither demonstrates causation or guarantees what an airline would charge if an input changed. /predict and /explain validate the same scenario against the same loaded artifact. The UI retains all contributions, even when only six appear as bars.
