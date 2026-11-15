# Project walkthrough

Phase 3 adds `src/skylens/quotes.py`, an offline intake beside the historical ML pipeline. It checks source permission, preserves raw/evidence hashes and separates verified candidates, research-only rows and malformed quarantine. It does not feed `train.py` or the API. The [collection guide](QUOTE_COLLECTION_GUIDE.md) and [final findings](../reports/phase3_final_findings.md) explain why no genuine quote, new airport or new model was claimed. For a source-only clone, start with [installation](INSTALLATION.md).
SkyLens is a local historical research application. A verified current INR total-fare predictor could not be established. Unknown currency, tax/passenger scope and booking journey type stay visible; source units are never labeled rupees.

**Research.** scripts/discover.py snapshots catalog searches; inspect_sources.py saves original cards; acquire.py downloads free versioned archives and a commit-pinned airport master. This solves traceability: every file can be identified by URL, version, hash and actual row count. Mirrored datasets do not add independent evidence.

**Preparation.** src/skylens/prepare.py reconciles the cabin raw/cleaned pair, parses dates/durations, joins reviewed city aliases and computes distance. Every removed record has an ID and reason. Input = retained + excluded. An unknown class does not become Economy, and missing quote settings do not become invented totals.

**Learning.** train.py separates training, validation, calibration and final testing. Training learns patterns; validation chooses a configuration; calibration measures residual size; final testing estimates errors after choices are fixed. Reusing the final test for choices would create an optimistic result. Baselines and three CatBoost settings are measured before selecting a model.

**Results.** Cabin final MAE: 2339.76 source units. Network: 2764.66. Full comparison and subgroup CSVs expose alternatives and weak cases. First's 144 rows are excluded. The wider network has no eligible exact profiles; the cabin model has 592 profiles across seven airports.

**Serving.** backend/app loads already-trained native models, checks file hashes and validates support. frontend/src retrieves options, sends a scenario and shows the actual output and native SHAP. Normal requests never train. The 88-airport observation set does not mean 88 supported airports.

**Verification.** Forty automated tests and the production TypeScript/Vite build pass. Browser permission was declined, leaving visual/mobile/interactive browser QA unverified. Raw files remain untouched. The deliverable is code plus evidence and boundaries, not a claim of nationwide live-price readiness.
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
