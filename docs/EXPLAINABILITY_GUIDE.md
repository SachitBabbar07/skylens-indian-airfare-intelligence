# Explaining an estimate
SHAP distributes a fitted model's output among input contributions relative to a baseline. In the saved actual cabin example, baseline 22917.85 plus contributions equals prediction 12483.34, in source units. The exact inputs and numbers are in models/cabin_2023/explanation_example.json and reports/explainability_report.md.

A positive contribution raises the output relative to the baseline; a negative contribution lowers it. This describes how the model used the inputs. It does not establish what caused the airline's price or promise a counterfactual price change. Correlated geography fields share information, so one coordinate's importance is not a causal discovery.

Global importance averages absolute native SHAP over real held-out rows. Permutation importance shuffles a validation input and measures its error increase using the selection-fit model. Local explanations use the exact validated request and the saved native model. All thirteen contributions are retained even when six are shown as bars. Automated checks confirm baseline plus contributions equals the actual prediction within 1e-6.
