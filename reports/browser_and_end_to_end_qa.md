# Browser and end-to-end QA — 15 November 2026

## Current follow-up: authorized browser QA passed

After the user updated permissions, both localhost origins opened successfully.
Desktop/mobile viewports, native predictions/SHAP, airport search, validation,
coverage, methodology, loading and outage/retry recovery were tested. The frontend
documentation proxy and numeric-field React warnings were fixed. Final normal-flow
console captures were empty; deliberate 422/outage 500 responses were inspected.
See the [complete follow-up and genuine screenshots](browser_qa_followup_20261115.md).
The earlier denial below is retained as historical Phase 2 evidence.

## Earlier Phase 2 browser result: blocked, not passed

The supported computer-use API first looked for an existing localhost tab, then
attempted to create an in-app browser tab for http://127.0.0.1:8000. The native
origin gate rejected it because **a saved user permission setting blocks the
action**. No alternate browser, raw CDP, Playwright/headless workaround, security
change or indirect browser execution was attempted.

Consequently desktop/mobile visual layout, horizontal overflow, autocomplete
keyboard interaction, actual UI loading/unavailable/error states, explanation
rendering, model/coverage screens, browser console and browser network panel
remain **unverified**. Filesystem/network command permissions do not override the
browser's separate saved policy. This report does not imply a screenshot exists.

## Permitted executed checks

| Check | Result |
| --- | --- |
| Checkpoint | D:\SkyLens\backups\phase2_20261115T060914Z; source/reports/metadata/models backed up, original data hashed |
| Unchanged baseline | 40 Python tests passed before implementation |
| Current suite | 48 passed, zero failures/errors; one upstream deprecation warning |
| run.ps1 | Existing unmodified workflow launched the local API successfully |
| Native artifacts | Checksums unchanged; model loading and real native output tests pass |
| Source-float minimum scenarios | 592 HTTP predictions pass |
| HH:mm minimum scenarios | 592 HTTP predictions pass after precision fix |
| HH:mm maximum scenarios | 592 HTTP predictions pass |
| Actual explanations | 592 HTTP explanations match their predictions and additive sums |
| Invalid API scenarios | 15 return the expected 422 |
| Assets | HTML, compiled JS/CSS and local SVG favicon return 200 |
| Currency contract | API currency null; result source explicitly labels source fare units |
| Airport states | Directory distinguishes no IATA, no fare evidence, other cohort, sparse profile and eligible research |
| Interval policy | No interval is emitted for the unvalidated serving domain |
| Frontend TypeScript/Vite | Production build passed |
| Data/leakage | Original data/models unchanged; original split disjointness and metrics verified |

Total measured API requests in the expanded matrix: 1776
predictions plus 592 explanations, with zero unexpected
failures. This is HTTP integration evidence, not DOM/browser end-to-end evidence.
The 592-profile source-float smoke test was also rerun separately.

## Reproduced defect and correction

Before the fix, seven default clock-converted scenarios returned 422 because
binary floats such as 1.6666666666666665 and 1.6666666666666667 represented the
same minute. The backend now permits a 1e-9-hour representation tolerance and
clamps it to the observed boundary. This is 3.6 microseconds, not an expansion to
a new fare/time category. A real one-minute out-of-range request remains rejected.
All seven original failures are regression-tested. See clock_precision_probe.json.

Browser QA still needs the normal saved-origin permission to be enabled by the
user or administrator. Until then, do not mark visual/interactive QA complete.
No paid service or cloud deployment was introduced.
