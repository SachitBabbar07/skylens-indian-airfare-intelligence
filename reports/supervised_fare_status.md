# Supervised fare prediction and hybrid source selection

**18 November 2026.** SkyLens has two trained research models and zero validated customer fare models. The private quote store has zero verified fare targets. A search can use comparable market observations when they are available. The evidence supports neither a trained blending model nor a claim about customer prediction accuracy.

## What the two models learned

The three original publisher metadata endpoints returned HTTP 200 and version 1 on 18 November. Each full description matched the previously archived description exactly. The frozen source CSV headers, target extraction, saved models, support tables and partition manifests were also checked. All 56 files in the preservation manifest matched their SHA-256 hashes. [Prior target audit and retrieval receipts](price_target_reaudit_20261115.md) · [Preservation manifest](../data/metadata/phase5/preservation_baseline.json)

| Cohort | Source evidence | Meaning of the target |
| --- | --- | --- |
| Cabin 2023 | The publisher describes an EaseMyTrip scrape covering seven airports. The raw file contains `Price`, and the cleaned file contains `Fare`. Preparation checks that the numerical values match in row order. [Publisher](https://www.kaggle.com/datasets/yashdharme36/airfare-ml-predicting-flight-fares) | Neither representation identifies currency, base versus total fare, tax and fee treatment, passenger basis or booking type. |
| Network 2020 | PromptCloud lists itinerary fields and `Fare`. Its export includes neither a cabin column nor any price-breakdown or booking-party field. [Publisher](https://www.kaggle.com/datasets/promptcloud/easemytrip-flight-fare-details-2020) | Currency and the same booking and price definitions remain unknown. |
| Later network challenge | A separate PromptCloud sample has the same fare schema and collector. It was used for a distribution-shift check outside fitting. [Publisher](https://www.kaggle.com/datasets/promptcloud/easemytrip-flight-fare-travel-listings) | The sample cannot supply independent, currency-verified labels. |

Single-direction rows do not establish that the recorded price purchased a one-way journey. Preparation retains the source number, leaves normalized INR missing, and records unknown price scope and passenger basis. [Preparation](../src/skylens/prepare.py)

## Reproduced holdouts and serving coverage

Both native CatBoost artifacts were loaded and used to score their saved final partitions with the shared training feature builder. The four categorical inputs are origin, destination, airline and cabin. The nine numerical inputs are stops, duration, days to departure, departure hour, distance and the four endpoint coordinates. The customer form supplies no itinerary duration, stops or scheduled departure hour, and can also leave airline unspecified. Substituting default itinerary features would change the prediction problem. [Feature builder](../src/skylens/features.py) · [Training pipeline](../src/skylens/train.py) · [Research serving gates](../backend/app/services.py)

| Model | Final test rows | MAE in source units | RMSE in source units | R² | Eligible research profiles | Final test rows inside serving gates |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| Cabin 2023 | 88,773 | 2,339.76 | 4,376.35 | 0.9470 | 592 | 0 |
| Network 2020 | 5,445 | 2,764.66 | 4,664.68 | 0.4266 | 0 | 0 |

Research serving requires at least 50 fitting observations for the exact directional route, airline, cabin and stops, plus training support for all three numerical itinerary inputs. Cabin qualifies on 42 directional routes across seven airports in Economy, Business and Premium Economy. Its fitting lead times span 1–35 days. Calibration spans 36–40 days and the final test spans 41–50 days. The largest network profile has 17 fitting observations. Neither model has an independently evaluated price interval for an accepted customer request. Airport-directory membership and the 88 airports with historical observations establish no additional model coverage. [Serving-domain audit](../data/metadata/phase2/serving_domain_check.json) · [Cabin model metadata](../models/cabin_2023/metadata.json) · [Network model metadata](../models/network_2020/metadata.json)

For one adult flying DEL → IXC, one way in Economy on 25 November 2026 with IndiGo, the cabin cohort has zero DEL → IXC rows. The network cohort contains 24, including one IndiGo record. The later challenge contains 38, including three IndiGo records. The two network sources omit cabin, and all three omit the required price definition.

## Evidence for selecting a source

The four Phase 2 candidate distributions are marked audit-only. The Phase 5 comparison also found no qualifying itinerary-level target. The India Cheap Flights Fare Index publishes CC BY 4.0 INR route aggregates. An earlier 18 November inspection recorded 1,554 route rows and 62 observations behind the DEL → IXC summary, with no individual flight, carrier or departure date to match to this request. None of these sources contributes paired outcomes. [Candidate registry](../data/metadata/phase2/new_source_registry.json) · [Candidate comparison](phase5_dataset_comparison.csv) · [Index publisher](https://indiacheapflights.com/press/)

The offline candidate runner targets observed one-adult, one-way Economy INR totals with taxes and fees included. It checks the frozen time split and source evidence, fits the training window, and scores against a route-and-carrier median baseline. Its existing software fixtures establish code behavior. With zero verified records in the workspace there are zero genuine matched observations containing a historical model prediction, a contemporaneous market reference and an independently observed target. A selector weight, route-specific winner or accuracy estimate cannot be fitted or evaluated. [Candidate runner](../src/skylens/train_verified_fare.py) · [Quote evidence](quote_data_quality_report.md)

A learned selector would need matching journey details, identical monetary definitions and rights to use the observations. Out-of-fold base predictions and as-of-time references must be paired to independent targets, then compared against using either source alone on a later holdout that excludes shared itineraries. Using a reference price as both an input and its own target would leak the answer. Until those data exist, use an approved model only within its validated group and summarize compatible observations where model coverage is unavailable.

## Why the earlier interface displayed individual offers

At commit `75bef9a`, the React flight form submitted to `useFlightSearch`, which posted the request to FastAPI's `/flights/estimate`. FastAPI checked the airport directory, then called `FareService.search`. Startup registered Kiwi and neither research artifact as a customer model. The service defaulted to Kiwi, returned its normalized `LiveQuote` records in a `results` array, and the React component mapped each entry to a `FlightResultCard`. Each card combined the literal label “API Fare” with `source_name` and showed a leg schedule and price. The separate experimental Groq endpoint asked a language model to generate bounds. It played no role in the Kiwi cards.

The Kiwi connector searches one-way or return itineraries for the specified passenger mix. Its product manager describes the displayed family-search price as the “total cost for all passengers.” The provider's live `tools/list` schema, inspected on 18 November without a fare search, specifies a single numerical price per itinerary, response-level currency and separate adult, child and infant counts. Together these support whole-party scope when the returned currency and passenger mix match. The schema supplies no tax or fee breakdown. A statistical range from this curated set describes the observed offers and carries no calibrated coverage probability. [Kiwi connector and passenger pricing](https://www.kiwi.com/stories/kiwi-mcp-connector/) · [Kiwi search tool](https://www.kiwi.com/en/pages/mcp/) · [Flight search API](../docs/API_GUIDE.md#flight-search)

## Acceptance checks on 18 November 2026

| Check | Observed result |
| --- | --- |
| Live one-way search | For DEL → IXC on 25 November, IndiGo Economy and one adult, the evening API response returned HTTP 200 with four distinct itineraries, Q1 ₹6,672, median ₹6,672 and Q3 ₹6,726.25. The browser rendered one market-based estimate. An earlier same-day lookup gave ₹6,678–₹7,003.25 from the offers available then. |
| Live return search | The same route returning 29 November, with two Economy adults, returned HTTP 200 with 12 distinct round-trip itineraries and a whole-party median of ₹27,340. |
| Production browser | Desktop and a 390-pixel mobile viewport showed one estimate and zero result links. The mobile document fitted the viewport. Stopping the backend produced an outage message. Restarting with `run.ps1` and using **Try again** restored the result with the entered itinerary. |
| Development browser | A component update preserved the itinerary and result through Vite hot reload. The final search produced no browser console warnings or errors. |
| Automated regression | 246 Python tests and 24 frontend tests passed, including the four selection cases with fixtures. Two Python test-client deprecation warnings remain. The TypeScript check and Vite production build passed. |

The live searches verified the market-estimation path and whole-party display at the time of lookup. The ML-only and dual-source paths used software fixtures because the workspace has no approved customer model. No Groq request was made.
