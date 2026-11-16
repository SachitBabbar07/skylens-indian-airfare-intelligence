# Frontend guide

SkyLens opens in **Research Mode**. The overview displays the required unavailable message, missing evidence and a disabled customer button. It displays no raw model amount. Metadata flags cannot promote a model into a customer predictor in this release.

The acquisition panel displays the dated evidence review and links to the empty quote CSV and source-permission schema. It does not present candidate rows as verified data or enable customer prediction. Missing or invalid status stays unavailable; the rest of Research Mode remains usable.

Coverage has separate historical route and eligible profile views. Use IATA, source and cabin filters to inspect observations; eligible profiles add carrier and stops filters and can open the matching research scenario. Dataset details display observed cabin labels and date ranges, including the separate external challenge. Neither a directory record nor a historical observation grants research support. The airport table and route tables have keyboard-focusable scroll regions.

Research tools, Coverage and Methodology remain available. `main.tsx` owns metadata loading, dependent inputs, comboboxes and directory state. `ResearchViews.tsx` owns customer status and research-only output presentation. Ordinary CSS and system fonts retain the existing responsive design.

Every airport, carrier, class and profile choice comes from the API. Endpoint changes choose an eligible route; cabin/carrier/stops depend on joint support. Defaults use observed field minima for a hypothetical historical profile, not an advertised flight or current schedule. At least 50 fitting observations and original numeric bounds remain required. The network cohort retains coverage and measured results without an eligible prediction form.

Raw output requires entering Research tools and acknowledging that values are unverified research outputs, not ticket prices or INR amounts. Submission clears stale output, calls `/research/predict` and `/research/explain`, then validates both responses. Currency must be null, research status true, verification unverified, numbers finite and output/explanation consistent. Unsafe responses are withheld. No conversion or sample-price fallback exists.

The former large fare card is removed. An ordinary diagnostics table shows raw output, baseline, support and withheld interval in **unverified model-output units**. SHAP does not express rupee increases or savings. All thirteen contributions and their additive check remain inspectable. MAE/RMSE use the same unverified units; R² is explained variance, not accuracy.

Search retains names/cities/codes, arrow keys, Enter and Escape. Required numeric fields stay empty when cleared; native range validation and backend checks remain. Loading, retry and errors do not invent output. Coverage retains search and pagination; tables scroll within mobile containers.

Run `npm --prefix frontend test` for rendered-component contract tests using existing React/Vite dependencies and Node's runner. Run `npm --prefix frontend run build` for TypeScript/production checks. Actual desktop/mobile QA and genuine screenshots are in the [correction report](../reports/product_correction_20261115.md). Older estimator screenshots are historical evidence of the superseded presentation.
