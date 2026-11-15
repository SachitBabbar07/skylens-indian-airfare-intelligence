"""Write phase-two reports from saved publisher snapshots and executed checks."""
from pathlib import Path
import hashlib
import json
import re
import xml.etree.ElementTree as ET
import zipfile

import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
O = ROOT / "data/metadata/phase2"
R = ROOT / "reports"
D = ROOT / "docs"


def write(path, text):
    path.write_text(text.strip() + "\n", encoding="utf-8")


def table(frame):
    clean = lambda value: str(value).replace("|", "/").replace("\n", " ")
    values = [[clean(value) for value in frame.columns]] + [
        [clean(value) for value in row] for row in frame.fillna("not established").values
    ]
    return "\n".join(
        ["| " + " | ".join(values[0]) + " |", "| " + " | ".join(["---"] * len(values[0])) + " |"]
        + ["| " + " | ".join(row) + " |" for row in values[1:]]
    )


def append_section(path, text):
    marker = "\n<!-- SKYLENS_PHASE2_START -->\n"
    original = path.read_text(encoding="utf-8").split(marker)[0]
    write(path, original.rstrip() + marker + text.strip() + "\n<!-- SKYLENS_PHASE2_END -->")


def main():
    semantics = json.loads((O / "fare_semantics.json").read_text())
    reconciliation = json.loads((O / "baseline_reconciliation.json").read_text())
    domain = json.loads((O / "serving_domain_check.json").read_text())
    overlap = json.loads((O / "candidate_overlap.json").read_text())
    eligibility = pd.read_csv(R / "airport_serving_eligibility_audit.csv")
    sensitivity = pd.read_csv(R / "serving_threshold_sensitivity.csv")
    generalization = pd.read_csv(R / "airport_generalization_phase2.csv")
    qa = json.loads((R / "phase2_http_integration.json").read_text())
    suite = ET.parse(R / "phase2_test_results.xml").find("testsuite")
    tests = int(suite.attrib["tests"])
    assert int(suite.attrib["failures"]) == int(suite.attrib["errors"]) == 0
    assert not qa["unexpected_failures"]
    checkpoint = json.loads((ROOT / "data/metadata/phase2_checkpoint.json").read_text())

    source_rows = []
    for cohort, info in semantics.items():
        card_path = O / ("card_" + info["source"].replace("/", "__") + ".json")
        card = json.loads(card_path.read_text())
        source_rows.append({
            "cohort": cohort, "publisher": card.get("ownerName"),
            "price_field": info["source_price_field"], "record_currency_field": "absent",
            "original_documented_default": "not found",
            "mixed_currency_test": "not possible from records",
            "decision": "Case C: unknown; no INR normalization",
            "card": "https://www.kaggle.com/datasets/" + info["source"],
        })
    currency_frame = pd.DataFrame(source_rows)
    currency_frame.to_csv(R / "fare_currency_audit.csv", index=False)
    write(R / "fare_currency_audit.md", f"""# Fare currency audit — 15 November 2026

The three selected cohorts still have **unknown currency**. This conclusion is
source-specific: original publisher descriptions were fetched again through the
public Kaggle API, public file-list metadata was inspected, and the untouched raw
price fields were checked. No separate record currency or explicit default was
found. Commas in a number, domestic geography, or today's EaseMyTrip defaults do
not establish the historic extraction currency.

{table(currency_frame)}

## Evidence chain

The original 2023 source is [Yash Dharme's dataset](https://www.kaggle.com/datasets/yashdharme36/airfare-ml-predicting-flight-fares).
Its raw Price column contains numeric strings; the card describes the fields and
collection method but does not assign a currency. The cleaned Fare column agrees
with raw prices, which verifies numeric preservation, not a monetary unit.
Original card snapshot: data/metadata/phase2/card_yashdharme36__airfare-ml-predicting-flight-fares.json.

Both [PromptCloud January/February](https://www.kaggle.com/datasets/promptcloud/easemytrip-flight-fare-details-2020)
and [April sample](https://www.kaggle.com/datasets/promptcloud/easemytrip-flight-fare-travel-listings)
cards enumerate Fare and itinerary fields without currency or extraction settings.
Their raw files have sixteen columns and no currency column. Linked DataStock
pages returned an application shell, without historical quote settings; no
authentication, paid access or restriction bypass was attempted. Public Kaggle
file descriptions/column dictionaries supplied no additional currency definition.
Snapshots and hashes are indexed in data/metadata/phase2/retrieval_log.json.

## Other assessed distributions

- The original [2022 Bathwal card](https://www.kaggle.com/datasets/shubhambathwal/flight-price-prediction)
  also does not explicitly establish the extraction unit. Academic reuse often
  labels it INR, but that is corroboration for that dataset, not a collector
  setting or permission to transfer the label to a different 2023/2020 file.
- The [MakeMyTrip sample](https://www.kaggle.com/datasets/andrewgeorgeissac/flight-price-data-of-indian-cities-makemytrip)
  explicitly excludes tax, but the inspected description/raw columns do not
  explicitly establish currency. Tax scope and currency are separate questions.
- The new [Ankush Sonar](https://www.kaggle.com/datasets/ankushsonar/flight-price-dataset-india-2019)
  and [Prithviraj Shukla](https://www.kaggle.com/datasets/prithvirajshukla/flight-fare-prediction)
  cards explicitly describe Price as INR. This is **publisher-declared INR for
  those mirror distributions**; original collection lineage/rights and full fare
  semantics remain unverified. The label is not silently transferred to the
  selected cohorts. All three inspected 2019 representations share 10,683 ordered
  airline/origin/destination/price keys. They are one family, not three independent
  sources. The Vivek Sharma representation itself does not document currency.
- The two new Air India revenue datasets explicitly declare INR but also declare
  synthetic generation. They cannot establish real fare observations.
- [Piratefly](https://huggingface.co/datasets/DeusHorizon/flight-fare-history)
  explicitly documents EUR, but publishes route/month aggregates under custom
  derived-data terms. [Flight Price Observatory](https://github.com/notlega/flight-price-observatory)
  documents SGD defaults and foreign SIN routes. Neither is an INR domestic
  itinerary target. No conversion was performed.

The difference between unknown and verified foreign currency matters: an
exchange-rate feed cannot determine a missing source unit. Any future conversion
must preserve original amounts, use an observation-date rate and record its
source. Today's rate would not repair these datasets. Model files, price values,
currency=null and normalized_price_inr=null remain unchanged.
""")

    semantic_rows = []
    for cohort, info in semantics.items():
        semantic_rows.append({
            "cohort": cohort, "target": "source-recorded listing fare",
            "currency": "unknown", "taxes_fees": "unknown", "passenger_basis": "unknown",
            "booking_journey_type": "unknown; directional record only",
            "cabin_labels": ", ".join(info["cabin_labels"]),
            "collection_days": len(info["collection_dates"]),
            "travel_dates": " to ".join(info["travel_dates"]),
            "collection_status": "single static query snapshot" if cohort == "cabin_2023" else "static sample of timestamped crawls",
        })
    semantic_frame = pd.DataFrame(semantic_rows)
    semantic_frame.to_csv(R / "fare_semantics_audit.csv", index=False)
    write(R / "fare_semantics_audit.md", f"""# Fare semantics audit — 15 November 2026

{table(semantic_frame)}

## What the number represents

The publisher describes scraped flight listings, not verified completed purchases.
The strongest description for the selected target is a **source-recorded listing
fare with undocumented price scope**. It cannot be advertised as a tax-inclusive
total, base fare, price per adult, full booking total or segment price. Even if INR
were independently established, these remaining questions would stay unresolved.
No division/multiplication by passenger count or summing reverse fares is valid.

The 2023 raw Airline-Class field contains actual Economy, Premium Economy,
Business and First labels. The source labels are preserved rather than inferred
from price; the 144 First rows remain excluded from fitting/serving. PromptCloud
does not record cabin, so Unspecified is a representation of missing information,
not a fourth verified cabin. Neither source records return settings, a priced
return itinerary or return dates. A directional itinerary is not proof of the
booking journey type.

## Time is not a transaction receipt

The 2023 Date of Booking field is 15 January 2023 for every raw row. Departure
dates are 16 January–6 March; arithmetic lead time is valid relative to that
source field, but does not prove an actual purchase occurred. There are no
independent changing query days. PromptCloud crawl timestamps provide three
January/February collection days and one April collection day after conversion
to Asia/Kolkata. They are observation times, not actual passenger booking times.
The advertised quarter is not substituted for the narrower dates in the files.

Canonical travel/collection dates, actual cabin labels and lead-time arithmetic
are documented in data/metadata/phase2/fare_semantics.json. Raw bytes and model
training targets were not edited.

## Potential alternatives

MakeMyTrip explicitly documents a base fare excluding taxes but lacks needed quote
settings/dates/class information. The 2019 mirror family documents INR in two
cards, without verified passenger, tax, booking or cabin scope. The 6,062-row
cleaned SSHRIYA source has booking dates but no cabin/currency documentation;
added Booking_Hour/Booking_DateTime provenance is not explained. Those hours
must not become authentic timestamps by assumption. Its five city labels do not
establish new airports beyond the existing 88. Synthetic Air India prices and
aggregate indices remain separate categories.

## Target decision, made before diagnostic fitting

See prediction_target_decision.md. Keep current research targets isolated and
retain the trained models. A future product target needs a documented currency,
total/tax/fee scope, adult-passenger basis, genuine journey type, cabin, query
time and departure date under usable source rights. Genuine returns need their
actual total and return date. No full retraining or currency relabeling is
justified by the current evidence.
""")

    airport_columns = ["iata_code", "origin_observations", "destination_observations",
                       "directional_routes", "network_2020_largest_profile",
                       "cabin_2023_eligible_profiles", "research_eligible"]
    write(R / "airport_serving_eligibility_audit.md", f"""# Airport serving eligibility audit

The original 88 observed airports and seven research-eligible airports are
reproduced from the actual data. There are **81 research-ineligible observed
airports and zero verified production-eligible airports**. All seven eligible
airports are AMD, BLR, BOM, CCU, DEL, HYD and MAA.

The companion airport_serving_eligibility_audit.csv contains **one row per observed
airport** with endpoint counts, directional routes, airline/operator labels,
classes, journey/currency/scope status, collection/travel span, missingness, quote
groups, per-model fitting observations and exact ineligibility reasons.

The wide 2020 source has 14,877 retained domestic rows before splitting, with
7,028 final fitting rows. It is fragmented into 2,401 route × carrier-label ×
class × stop cells; the largest has only 17 fitting rows. No network cell passes
50. Carrier combinations are retained as original labels, not invented single
airlines. The later 22,735-row challenge never contributes fitting support.

The cabin source has 445,366 deduplicated observations, including 144 rare First
rows excluded from modeling. Train+validation fit 311,968 rows and provide 592
eligible exact cells across its seven airports. Sources with missing cabins or
uncertain price definitions cannot simply be appended to fill sparse cells.

## Missingness and independence

Core retained numeric/categorical inputs have no nulls after documented filters.
That is not complete semantics: currency and price scope are undocumented for
100% of selected observations; network cabin is Unspecified. Distinct quote
fingerprints eliminate exact duplicates but do not establish statistical
independence. Shared flights, routes and collection days induce dependence.
Cabin's single collection day and network's three fitting-candidate days are
especially limiting; counts are observations, not independent booking events.

## Threshold review

Fifty is an operational research heuristic, **not statistically established
reliability**. The following new experiment fits training only and measures the
unchanged validation partition with 250-tree diagnostic models. It does not use
the final test or change serving eligibility. Counts here use training-only
support; the deployed support CSV includes the final train+validation fit, so
579 diagnostic cabin cells at threshold 50 are not a contradiction of 592 served
cells.

{table(sensitivity[["cohort", "minimum_profile_count", "fitting_airports", "eligible_profiles", "validation_rows", "mae"]].round(3))}

Numeric serving bounds are deliberately not applied in this diagnostic; cabin
validation itself is outside the training lead window. These scores cannot
validate a replacement serving rule. Network threshold five admits 50 airports
but only 420 validation rows from one collection day; threshold ten has only
11. Different threshold rows select different subsets, so a lower MAE is not an
apples-to-apples improvement. Currency/target gaps remain regardless of counts.
No evidence justifies lowering the current rule or promoting a rejected airport.

Better future rules need independent query-day/flight-date clusters, route/class
error and interval calibration within the accepted numeric domain, and an
untouched time period. They should measure distinct itinerary support rather
than treating every correlated row as an independent sample.

## Exact per-airport summary

Network maximum is the largest fitting profile touching that endpoint; cabin
cells count eligible profiles touching it. Each row's full explanation and
temporal/semantic measures are in the CSV.

{table(eligibility[airport_columns])}
""")

    profiles = json.loads((O / "new_file_profiles.json").read_text())
    inventory_rows = []
    decisions = {
        "viveksharmar/flight-price-data": "2019 derivative; undocumented currency/quote settings.",
        "ankushsonar/flight-price-dataset-india-2019": "Publisher-declared INR; same ordered 2019 keys, unclear upstream lineage and malformed arrival date.",
        "prithvirajshukla/flight-fare-prediction": "Publisher-declared INR; same 2019 family, no passenger/tax/booking scope; provenance claim unverified.",
        "sshriya08/flight-price-prediction-dataset": "No documented currency/cabin or added booking-hour provenance; source lineage unresolved.",
    }
    for ref, decision in decisions.items():
        card = json.loads((O / ("candidate_" + ref.replace("/", "__") + ".json")).read_text())
        owned = [value for value in profiles if value["source"] == ref]
        inventory_rows.append({
            "candidate": ref, "category": "G: audit only", "downloaded": True,
            "actual_files": "; ".join(f"{Path(value['path']).name}: {value['rows']:,} rows" for value in owned),
            "license_declared": card["licenseName"],
            "source": "https://www.kaggle.com/datasets/" + ref, "decision": decision,
        })
    extra_candidates = [
        ("Air India revenue management 1m", "synthetic", "CC0", "https://www.kaggle.com/datasets/aryansingh2000/air-india-revenue-management", "Original card explicitly describes simulated/synthetic data. Not downloaded or trained."),
        ("Air India revenue management 50m", "synthetic", "CC0", "https://www.kaggle.com/datasets/aryansingh2000/air-india-revenue-management-data-analytics", "Explicitly synthetic; advertised scale is not authentic fare evidence."),
        ("Mohit Tomar raw fare source", "G", "Unknown", "https://www.kaggle.com/datasets/mohittomar2008/flight-price-prediction-through-webscrapping", "Card inspected; original reuse rights and currency unestablished. No restricted file acquisition."),
        ("SIH India airfare index", "G: demo", "No repository license found", "https://github.com/keyholder1/sih-india-airfare-price-index", "Example generator explicitly fabricates prices; no real fare CSV in inspected data tree. Not trained."),
        ("TOI-DPA index", "F", "Raw reuse terms not established", "https://www.decimalpointanalytics.com/what-we-do/data-science-and-ai/toi-dpa-airline-price-index", "56-route descriptive economy index; no accessible licensed itinerary microdata established."),
        ("India Cheap Flights index", "F", "CC BY 4.0 stated", "https://indiacheapflights.com/press/", "Aggregated usual fares/ranges. Raw JSON request returned 403; no bypass or file-content claim."),
        ("Piratefly fare history", "F", "Custom Travelpayouts-derived terms", "https://huggingface.co/datasets/DeusHorizon/flight-fare-history", "Explicit EUR one-way aggregates, not compatible itinerary observations."),
        ("Flight Price Observatory", "out of geography", "Apache-2.0 code; underlying data rights not established here", "https://github.com/notlega/flight-price-observatory", "Documents SGD and SIN foreign routes/returns; no Indian domestic coverage in described catalog."),
        ("MoSPI CPI collection methodology", "methodology", "Not an observation dataset", "https://www.mospi.gov.in/uploads/documents/documents/1769670534541-Export_report_CPI.pdf", "Useful one-adult one-way economy collection definition; no downloadable individual fare observations found."),
    ]
    for title, category, license_name, url, decision in extra_candidates:
        inventory_rows.append({"candidate": title, "category": category, "downloaded": False,
                               "actual_files": "not downloaded", "license_declared": license_name,
                               "source": url, "decision": decision})
    inventory = pd.DataFrame(inventory_rows)
    inventory.to_csv(R / "second_round_dataset_inventory.csv", index=False)
    retrievals = json.loads((O / "retrieval_log.json").read_text())
    discovered = {value["ref"] for item in retrievals if item["name"].startswith("kaggle_search")
                  for value in item.get("results", [])}
    write(R / "second_round_dataset_research.md", f"""# Second-round dataset research

Bounded search performed 15 November 2026. Seven public Kaggle queries returned
{len(discovered)} distinct references; Hugging Face searches, GitHub source trees,
and web searches targeting Zenodo, Figshare, OpenML, government, official/academic
sources were also reviewed. No qualifying additional Indian domestic return-price
file or compatible verified total-per-passenger dataset was found. This is not a
claim that all internet datasets were exhausted.

Four new publicly licensed distributions were downloaded into data/raw/phase2,
with immutable archives, extracted-file hashes, actual schemas/missingness/samples,
and audit-only entries in the main registry. None enters training or coverage.
The bundled 83,259-row airport file is metadata, lacks an IATA column in this
distribution and does not expand fare evidence.

{table(inventory)}

## Duplicate and authenticity findings

The Vivek Sharma, Ankush Sonar and Prithviraj Shukla representations each contain
10,683 rows. Their ordered airline/source/destination/price keys agree **100%**.
This is documented key overlap, not a false assertion that every byte/column is
identical. The CSV copies transform dates/routes; the Ankush sample even contains
a 2025 arrival timestamp for a 2019 journey. These are one source family, with
upstream provenance/licensing unresolved, not independent external validations.
See data/metadata/phase2/candidate_overlap.json and new_file_profiles.json.

The SSHRIYA source has 6,062 fare rows and five city labels. Its card does not
explain added booking-hour/time/slot columns. They are not accepted as authentic
query timestamps. The two large Air India cards explicitly declare synthetic
generation despite attractive INR/First/premium fields; no synthetic fares were
downloaded into training or evaluated as real performance. The SIH example
generator also explicitly identifies its prices as fabricated demonstration
values; no real price file was located in its inspected data tree.

## Access, currency and compatibility

Original source cards/public APIs were inspected, not just titles. The selected
sources remain currency-unknown. Some new mirror publishers explicitly declare
INR, but that does not repair their other semantics or establish the selected
datasets' unit. EUR aggregates and foreign SGD itineraries stay separate; no
historical FX conversion is needed because no compatible foreign quote cohort
is being incorporated.

India Cheap Flights' JSON download returned HTTP 403. DataStock links returned
an application shell. The MoSPI PDF fetch timed out, while indexed official
methodology text was available. No login, paid API, scraping bypass or browser
permission workaround was used. Government traffic/schedule/methodology sources
do not become fare training records. Query/result snapshots and source cards
are saved under data/metadata/phase2.

**Decision:** no new source is incorporated into the model. Existing models,
training rows, source targets, 88 observed airports and seven research-serving
airports remain unchanged. The new evidence improves rejection/provenance
decisions, not supported-airport counts.
""")

    old_stress = pd.concat([
        pd.read_csv(R / f"{name}_generalization.csv").assign(cohort=name)
        for name in ["network_2020", "cabin_2023"]], ignore_index=True)
    write(R / "model_reliability_phase2.md", f"""# Model reliability review

Saved final-test metrics were recomputed from every saved actual/prediction pair.
They match both metadata files. A fresh native prediction sample of 100 real
test rows per model matches the saved predictions. All original data/model hashes
and all six split-pair quote/fingerprint disjointness checks pass. See
data/metadata/phase2/baseline_reconciliation.json.

Existing random, route, airport and temporal results are preserved. Per-airport,
route, carrier, class, journey label, booking window, price and duration subgroup
errors remain in the original subgroup CSVs. Different protocols/250-tree stress
fits are not falsely compared as the same final model.

{table(old_stress[["cohort", "protocol", "n", "mae", "rmse"]].round(3))}

## Explicit generalization categories

1. Known airports and observed route: the retained cabin research product; still
   unverified target semantics and no independent final-test rows inside its
   numeric serving domain.
2. Known airports, unseen directional route: existing route-grouped diagnostics
   have errors around 4,385–4,489 cabin source units. Reverse routes may still
   exist in training; this is not an unseen undirected airport pair guarantee.
3. One unseen endpoint: existing leave-airport diagnostics plus the new two-held
   airport experiment below.
4. Both endpoints unseen: now explicitly separated in a development-only
   two-airport holdout.
5. Insufficient evidence: sparse/unknown combinations remain blocked. The network
   model has no eligible exact serving profile.

The new experiment holds out the two most frequent airports based on observation
counts only, removes every row touching either from fitting, and separately
evaluates one versus both unseen endpoints. It uses 250-tree diagnostic models,
the unchanged source targets, and only train/validation development rows.

{table(generalization[["cohort", "category", "held_airports", "n", "mae", "rmse"]].round(3))}

Network has only 25 both-unseen rows for its chosen pair, so that low sample error
cannot establish reliability. Cabin's both-unseen error is about 5,046 source
units, substantially worse than familiar-domain diagnostics. Neither airport-pair
experiment represents all unseen airports. No new-route or unseen-airport serving
is enabled.

## Serving-domain correction

{table(pd.DataFrame([{"cohort": name, **record} for name, record in domain.items()]))}

Cabin fitting leads are 1–35 days, calibration 36–40 and test 41–50. All 88,773
final-test rows are outside the API's accepted support ranges. The old 89.24%
offline interval coverage is correctly measured, but **does not validate an
interval for an accepted user request**. Aggregate coverage and a route row count
were insufficient gates. The API now withholds intervals and explains why;
offline artifacts/metrics and point research estimates are preserved.

No full retraining or model replacement is justified. Priority is documented
quote semantics and fresh independent query-day observations, followed by
calibration/evaluation within the intended serving domain. Larger datasets,
geographic features and lower row thresholds cannot substitute for those checks.
""")

    write(R / "browser_and_end_to_end_qa.md", f"""# Browser and end-to-end QA — 15 November 2026

## Browser result: blocked, not passed

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
| Checkpoint | {checkpoint["checkpoint_dir"]}; source/reports/metadata/models backed up, original data hashed |
| Unchanged baseline | 40 Python tests passed before implementation |
| Current suite | {tests} passed, zero failures/errors; one upstream deprecation warning |
| run.ps1 | Existing unmodified workflow launched the local API successfully |
| Native artifacts | Checksums unchanged; model loading and real native output tests pass |
| Source-float minimum scenarios | 592 HTTP predictions pass |
| HH:mm minimum scenarios | 592 HTTP predictions pass after precision fix |
| HH:mm maximum scenarios | 592 HTTP predictions pass |
| Actual explanations | 592 HTTP explanations match their predictions and additive sums |
| Invalid API scenarios | {len(qa["expected_invalid_requests"])} return the expected 422 |
| Assets | HTML, compiled JS/CSS and local SVG favicon return 200 |
| Currency contract | API currency null; result source explicitly labels source fare units |
| Airport states | Directory distinguishes no IATA, no fare evidence, other cohort, sparse profile and eligible research |
| Interval policy | No interval is emitted for the unvalidated serving domain |
| Frontend TypeScript/Vite | Production build passed |
| Data/leakage | Original data/models unchanged; original split disjointness and metrics verified |

Total measured API requests in the expanded matrix: {qa["prediction_requests"]}
predictions plus {qa["explanation_requests"]} explanations, with zero unexpected
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
""")

    summary = f"""## Phase-two findings — 15 November 2026

The existing trained models and original data are preserved. The baseline again
passed 40 tests; the current suite passes {tests}. HTTP QA passed 1,776 predictions
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
- Browser access is still denied by a saved permission setting. Visual/mobile/
  interactive QA, console and browser network checks remain unverified.

Read [currency](reports/fare_currency_audit.md), [fare semantics](reports/fare_semantics_audit.md),
[airport eligibility](reports/airport_serving_eligibility_audit.md),
[new source research](reports/second_round_dataset_research.md),
[model reliability](reports/model_reliability_phase2.md) and
[QA](reports/browser_and_end_to_end_qa.md). No full model retraining or serving
expansion was justified. Next work should obtain documented real quotes and
independent query-day evaluation in the intended input domain.
"""
    write(D / "PHASE2_FINDINGS.md", summary.replace("(reports/", "(../reports/"))
    append_section(ROOT / "README.md", summary)
    readme = (ROOT / "README.md").read_text(encoding="utf-8")
    notice = f"""<!-- SKYLENS_PHASE2_NOTICE -->
> **Current audit:** {tests} tests pass; models and original data are preserved.
> Served intervals are withheld because the holdout does not validate the accepted
> input range. Currency/full fare scope remain unknown; browser QA is blocked.
> See [phase-two findings](docs/PHASE2_FINDINGS.md) for the current status.
<!-- SKYLENS_PHASE2_NOTICE_END -->
"""
    readme = re.sub(r"<!-- SKYLENS_PHASE2_NOTICE -->.*?<!-- SKYLENS_PHASE2_NOTICE_END -->\s*",
                    "", readme, flags=re.S)
    write(ROOT / "README.md", readme.replace("# SkyLens\n", "# SkyLens\n\n" + notice + "\n", 1))
    append_section(D / "PHASE2_FINDINGS.md", """## Reproduce this audit in the preserved workspace

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
""")
    corrections = """## Phase-two correction — 15 November 2026

The original report above records phase-one results. Phase-two inspection
confirmed its numeric metrics but found zero cabin final-test rows inside the
current numeric serving domain (fit lead days 1–35, test 41–50). The old aggregate
interval gate is no longer used: API intervals are withheld. Seven clock-float
boundary rejections were fixed; genuine out-of-range values remain rejected.
Training data/model artifacts, the 50-row rule and the 88-observed/7-research/
0-production airport counts remain unchanged. See model_reliability_phase2.md,
airport_serving_eligibility_audit.md and browser_and_end_to_end_qa.md.
"""
    for name in ["model_evaluation_report.md", "airport_coverage_report.md",
                 "route_coverage_report.md", "final_project_report.md"]:
        append_section(R / name, corrections)
    for name in ["PROJECT_WALKTHROUGH.md", "ML_MODEL_GUIDE.md", "API_GUIDE.md",
                 "FRONTEND_GUIDE.md", "EDGE_CASES_AND_VALIDATION.md", "VIVA_PREPARATION.md"]:
        append_section(D / name, """## Phase-two update

See PHASE2_FINDINGS.md for the current audit. Currency and full fare scope remain
unknown. The API now withholds intervals because the historical final holdout
does not overlap its serving ranges; it exposes /fare-semantics and explicit
airport serving statuses. Seven clock-rounding rejection cases were fixed with
microsecond-scale normalization. Tests and HTTP checks pass; browser QA remains
blocked by the saved permission policy. Existing models and training data were
preserved, and no wider serving or full retraining was justified.
""")
    # Record precise changed baseline files, retaining every original data/report.
    checkpoint_dir = ROOT / "backups" / Path(checkpoint["checkpoint_dir"]).name
    baseline = json.loads((checkpoint_dir / "baseline_manifest.json").read_text())
    changed, immutable, replaced_build_assets = [], [], []
    for name, old in baseline["files"].items():
        path = ROOT / name
        if not path.exists() and name.startswith("frontend/dist/assets/"):
            # Vite replaces content-hashed generated bundles. The checkpoint
            # preserves their exact bytes; this exception never applies to
            # source files, reports, observations or model artifacts.
            with zipfile.ZipFile(checkpoint_dir / "checkpoint.zip") as archive:
                assert hashlib.sha256(archive.read(name)).hexdigest() == old["sha256"]
            replaced_build_assets.append(name)
            continue
        assert path.exists(), f"Original source/data/report removed: {name}"
        current_hash = hashlib.sha256(path.read_bytes()).hexdigest()
        if current_hash != old["sha256"]:
            changed.append(name)
        if name.startswith(("data/raw/", "data/processed/", "data/interim/", "models/")):
            assert current_hash == old["sha256"], name
            immutable.append(name)
    result = {
        "checkpoint": checkpoint, "baseline_tests": 40, "current_tests": tests,
        "original_immutable_files_verified": len(immutable),
        "model_binaries_and_metadata_changed": False,
        "research_eligible_airports": int(eligibility.research_eligible.sum()),
        "observed_airports": len(eligibility), "production_eligible_airports": 0,
        "new_training_rows": 0, "full_model_retraining": False,
        "audit_only_new_distributions": 4, "changed_baseline_files": changed,
        "generated_assets_replaced_and_preserved_in_checkpoint": replaced_build_assets,
        "http_prediction_requests": qa["prediction_requests"],
        "http_explanation_requests": qa["explanation_requests"],
        "http_unexpected_failures": len(qa["unexpected_failures"]),
        "intervals": "withheld_unvalidated_serving_domain",
        "browser_qa": "blocked by saved permission policy",
    }
    write(R / "phase2_final_audit.json", json.dumps(result, indent=2))
    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()
