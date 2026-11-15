## Phase-two findings — 15 November 2026

Follow-up: the earlier browser restriction described below was resolved after
the user updated permissions. Both origins now pass the documented desktop/mobile
[browser QA follow-up](../reports/browser_qa_followup_20261115.md). Phase 2 numbers
below remain the historical baseline; the current Python suite has 102 tests.

The existing trained models and original data are preserved. The baseline again
passed 40 tests; the current suite passes 48. HTTP QA passed 1,776 predictions
and 592 real explanations across all 592 offered profiles, plus expected invalid
requests. The existing run.ps1 workflow and production build pass.

- Original source cards/raw files still do not establish currency, taxes,
  passenger basis or booking journey type for selected cohorts. No INR relabeling
  or FX conversion was made.
- Four new distributions were inspected as audit-only data. Three share identical
  ordered 2019 common keys; others have unresolved semantics. Large Air India
  candidates explicitly declare synthetic generation. No new training data qualified.
- The 88/7 coverage gap is reproduced per airport: the broader network has no
  exact fitting cell above 17 observations. Lower thresholds lack adequate
  independent validation and were not adopted.
- A reliability correction withholds served intervals: the cabin final holdout
  is at lead days 41–50, outside the accepted 1–35 fitting range. Offline coverage
  remains available but cannot validate an accepted scenario's range.
- The seven clock-rounding failures are fixed without weakening real bounds.
- Browser access was denied at the Phase 2 audit. That restriction was later
  resolved; see the current authorized browser follow-up linked above.

Read [currency](../reports/fare_currency_audit.md), [fare semantics](../reports/fare_semantics_audit.md),
[airport eligibility](../reports/airport_serving_eligibility_audit.md),
[new source research](../reports/second_round_dataset_research.md),
[model reliability](../reports/model_reliability_phase2.md) and
[QA](../reports/browser_and_end_to_end_qa.md). No full model retraining or serving
expansion was justified. Next work should obtain documented real quotes and
independent query-day evaluation in the intended input domain.
<!-- SKYLENS_PHASE2_START -->
## Reproduce this audit in the preserved workspace

Keep the local backups checkpoint when copying the workspace; its location is
resolved relative to the project, not a hard-coded machine directory. The new
preservation tests intentionally compare the pre-phase model/data bytes. Fresh
training creates a new experiment requiring its own validation/checkpoint;
it must not silently overwrite the frozen phase-two evidence.

Run scripts/phase2_audit.py, scripts/phase2_diagnostics.py, the full pytest suite,
the frontend build, the existing run.ps1 server, scripts/phase2_http_qa.py and
scripts/phase2_reports.py. New audit-only file replays use
scripts/phase2_acquire_candidates.py and saved publisher snapshots. Original
acquisition/report commands preserve audit-only registry entries without adding
them to config/sources.json. No new source is read by model training.
<!-- SKYLENS_PHASE2_END -->
