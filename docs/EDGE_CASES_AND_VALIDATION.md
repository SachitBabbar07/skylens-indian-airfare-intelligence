# Edge cases and validation
Forty executed tests cover native fitted-model outputs and SHAP additivity, missing fields, malformed JSON, invalid types/ranges, unknown IATA/ICAO, same endpoints, unsupported class/carrier/journey, extra dates/return/passenger fields, failed artifacts, safe internal errors, search/metadata, exclusion accounting, duplicate/quote separation and unknown currency preservation.

The sparse network is an expected restriction: its fitted outputs can be evaluated offline while the API blocks profiles below fifty observations. Tests verify both behaviors without lowering the gate. Support uses training+validation fitting rows, never test membership. Missing/corrupt artifact fixtures stay in a temporary test folder; malformed requests and corrupt bytes are the only synthetic test data, and none enter learning or metrics.

Real domestic return, same-day return and multi-city flows cannot be asserted as supported without data. They are rejected by schema restrictions. Unknown cabin labels do not become Economy. The final split manifests and reports/test_results.xml are independently inspectable.

The production TypeScript build passes, but browser permission was declined. Interactive/mobile/visual QA remains outstanding and must precede any production-readiness claim.


Additional executed checks: 592 advertised profiles passed real HTTP prediction with 0 failures; 2 compiled frontend assets and the HTML page returned HTTP 200. All 26 original file hashes match. Frozen-version acquisition was rerun successfully without raw overwrites. These checks do not replace the declined browser QA.
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
