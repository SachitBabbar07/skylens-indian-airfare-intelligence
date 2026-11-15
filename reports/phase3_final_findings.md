# Phase 3 findings

The legitimate-access investigation did not establish an available INR-0 source with permission to collect, retain and use genuine Indian domestic quotes for this ML experiment. **No new genuine quote was acquired.** The [source audit](quote_source_access_audit.md) records official references, credentials/cost/access restrictions, retention/ML uncertainties and decisions. The importer and sampling design are complete; the data-acquisition dependency remains open.

## Plain-language outcome

| Question | Result |
| --- | --- |
| Where did new real quotes come from? | None. No airline/partner quote endpoint was queried and no page was copied for quote data. |
| Which source granted collection/reuse? | None in this session. Manual entry also needs source permission. |
| What do the new prices mean? | No actual new price exists. The initial candidate target is an evidenced all-in INR total for one adult, separately one-way or an actual return booking. |
| Was currency verified? | Zero new currency-verified targets; historical model currency stays null/source units. |
| Taxes, fees and passenger basis established? | Zero new observations with these meanings established. The importer requires all three before verified-target status. |
| Genuine return bookings obtained? | Zero. The workflow never constructs a return target from opposite one-way prices. |
| More airports eligible? | No. AMD, BLR, BOM, CCU, DEL, HYD and MAA remain research-eligible; production eligibility remains zero. |
| Model improved or retrained? | No retraining and no new accuracy improvement claim. Both artifacts/metadata/support are unchanged. |
| Uncertainty restored? | No. Intervals remain withheld until independently validated in the accepted domain. |
| Budget | INR 0; no paid API, subscription, ticket or paid runner configuration introduced. |

## Implemented deliverables

- [Permission/source audit](quote_source_access_audit.md), [canonical schema](quote_collection_schema.md) and [representative collection plan](quote_collection_plan.md).
- Offline `python -m skylens.quotes` template/schema/validate/ingest/summary/freeze-split commands. Raw/evidence/permissions stay in ignored private storage, immutable hashes/replay receipts preserve history, and conflicts are excluded. No training/serving hook or scraper.
- Header-only [CSV](../config/quote_template.csv), machine-readable [schema](../config/quote_schema.json), empty permission configuration and [entry guide](../docs/QUOTE_COLLECTION_GUIDE.md).
- [Quality](quote_data_quality_report.md), [variability](quote_variability_analysis.md), [every-airfield evidence](new_airport_evidence_report.md), [retraining decision](phase3_retraining_decision.md) and [model validation](phase3_model_validation.md). Statistical results requiring real new prices are explicitly not estimable.
- Git ignores/scans, code-only MIT license, contribution/changelog/installation guides and commit-pinned portable GitHub Actions. Actual authentication/repository/push/CI results are kept in [GitHub delivery](github_delivery_report.md), without claiming unexecuted remote work.

## Executed verification

The untouched baseline passed 48 tests. The final local suite passed **102 tests**: all original 48 plus 54 portable software checks, with zero failures/errors/skips and one upstream deprecation warning. Tests cover native model loading/prediction/SHAP, data leakage/preservation and the new intake. The actual private remote was cloned into a clean source-only checkout: all 54 portable tests, compilation and documentation-link checks passed without model/data dependencies. Detailed outcomes are in [verification](phase3_verification.json).

TypeScript/Vite production builds passed in the original workspace and clean clone. Clean installation exposed an existing Vite development-tool vulnerability; Vite was pinned from 6.3.5 to patched 6.4.6 within the same major version. The reviewed lockfile changes only Vite, npm audit now reports zero known vulnerabilities, and all four compiled application files were byte-identical after the patch. No application-source, model or data change was involved. See [dependency audit](frontend_dependency_audit.json) and the [maintainer advisory](https://github.com/vitejs/vite/security/advisories/GHSA-p9ff-h696-f583). The unchanged `run.ps1` launched both actual native models with health 200; the owned server was stopped after testing.

The HTTP matrix passed **1,776 predictions + 592 additive explanations + 15 expected invalid-input cases**, with zero unexpected failures, across all 592 exposed profiles; metadata, directory and built assets passed. The original 592-profile HTTP smoke also passed separately. These are real local native-model requests, not mock results, and are distinct from the synthetic portable contract tests.

Original raw/processed/interim data and all model files were compared with the Phase 3 checkpoint: **56 unchanged files**. Model hashes and original metrics are in the validation report. Registry publication removes individual source examples while retaining source schemas/hashes/licenses; the original local baseline/checkpoints preserve those examples and are never pushed.

## GitHub backup

[SachitBabbar07/skylens-indian-airfare-intelligence](https://github.com/SachitBabbar07/skylens-indian-airfare-intelligence) is **PRIVATE**, with `main` as default branch. Milestone pushes, matching remote commit, uploaded source/docs and GitHub-rendered README were verified. The [delivery report](github_delivery_report.md) contains identity/authentication, branches, commits, exclusions, reconstruction and clone/pull/contribution instructions. No secret, raw dataset, quote evidence, model binary, backup or local audit branch was uploaded.

Hosted Actions jobs are **skipped by the zero-spend gate**, as explicitly requested by the user after billing availability could not be confirmed. No CI pass is claimed. No completion tag was created; quote-source acquisition remains an open dependency.

## Authorized browser follow-up

The earlier permission denial was resolved after the user updated the saved permissions. Both `http://127.0.0.1:8000` and `http://127.0.0.1:5173` now open through the authorized in-app browser. Desktop and mobile viewport flows, real estimates/SHAP, airport search, validation, directory/methodology and loading/outage/retry recovery passed. The frontend documentation proxy and blank-number React warning were fixed and retested. No browser security restriction was bypassed.

See [the follow-up report and genuine screenshots](browser_qa_followup_20261115.md). Final healthy-flow console captures were empty; deliberate HTTP 422 and outage-related HTTP 500 responses were inspected separately. A complete Network/HAR interface is unavailable, so response inspection used the live Swagger panel and correlated server logs. Physical mobile devices and other browser engines remain untested. No localhost permission issue remains observed.

## What remains unsupported

Live/current verified INR prediction, genuine one-way booking or return/multicity serving, additional airports, sparse profiles/First Class, population-wide reliability and served uncertainty remain unsupported. The next useful work is an actual collection/storage/ML permission grant or independently licensed authentic quote file, followed by the preregistered repeated-day experiment, conflict review and independent evaluation. The importer cannot supply missing rights or evidence.
