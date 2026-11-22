# Indian airport and fare-estimation coverage

The Flights directory contains **165 Indian IATA endpoints**, giving **27,060 directed routes** between different airports. A customer can search any pair. A market reference requires comparable provider observations for that specific search. [Flights airport directory](../backend/app/flight_search.py)

| Evidence in the repository | Airports | Directed routes |
| --- | ---: | ---: |
| Searchable IATA codes and their possible pairs | 165 | 27,060 |
| One or more retained historical listings | 88 | 720 |
| One or more rows used to fit either saved CatBoost model | 83 | 677 |
| At least one historical profile meeting the research count threshold | 7 | 42 |
| Validated customer fare model | 0 | 0 |

Of the 720 routes with listings, **43 contributed no rows to either final fit**. For example, AGR → DEL has 11 retained listings and zero fitting rows. DEL → IXC has 62 retained listings and 12 network-model fitting rows. No exact profile on that route meets the research threshold. [Historical listings](route_fare_coverage.csv) · [Network fit profiles](../models/network_2020/support.csv) · [Cabin fit profiles](../models/cabin_2023/support.csv)

## Recorded provider coverage

On 19 November 2026, nine Kiwi.com searches covered eight directed routes. Eight searches produced comparable INR observations, and one completed with no usable observations. **27,052 directed routes have no recorded provider check.** The searches used Economy, any airline and adults only. Dates below are in 2026. [Dated probe results](market_probe_results.json)

| Route | Departure | Return | Adults | Comparable observations | Result for this request |
| --- | --- | --- | ---: | ---: | --- |
| BOM → BLR | 26 Nov | — | 1 | 15 | INR market reference with interquartile range |
| BOM → BLR | 3 Dec | 6 Dec | 2 | 15 | INR market reference with interquartile range |
| CCU → IXB | 5 Dec | 9 Dec | 1 | 15 | INR market reference with interquartile range |
| DEL → IXC | 26 Nov | — | 1 | 7 | Limited-sample INR market reference |
| GAU → IMF | 2 Dec | — | 1 | 3 | Limited-sample INR market reference |
| IXA → JAI | 3 Dec | — | 1 | 3 | Limited-sample INR market reference |
| IXB → CCU | 1 Dec | — | 1 | 1 | Single comparable INR observation |
| MAA → CJB | 28 Nov | — | 2 | 4 | Limited-sample INR market reference |
| SLV → IXC | 7 Dec | — | 1 | 0 | Estimate unavailable, no provider observations |

## Reproduce the full inventory

From the repository root, run the following offline command with Python 3.12.

```console
python scripts/build_market_coverage.py
```

The command writes three CSVs to `data/cache/market_coverage/`. Use `--output-dir PATH` to change the directory. The input tables and dated probe summaries are versioned. The export requires no provider credentials, network access, private datasets or model binaries. [Report generator](../scripts/build_market_coverage.py)

| File | Rows and interpretation |
| --- | --- |
| `airports.csv` | One per IATA endpoint. Includes name, city, state, listing rows, fitting rows by model, research-eligible profiles, customer ML eligibility and count of incident directed routes with a recorded check. A route contributes to both endpoints. |
| `routes.csv` | One per ordered origin and destination. Includes the same history and eligibility measures, number of recorded checks, and whether dated evidence exists. Filtering by the two airport codes keeps the trip direction. |
| `requests.csv` | One per recorded search and retrieval time. Includes dates, journey, cabin, airline filter, adult/child/infant composition, provider status, comparable observation count, currency compatibility, final method and unavailable reason. Join to the route matrix on both IATA codes. |

## How to interpret a route

Historical listings count all retained observations across the selected sources, including the later external challenge. Final fitting counts sum the saved profile counts over the training and validation partitions. The network model used 7,028 fitting rows and the cabin model used 311,968. Calibration, test and external challenge records do not enter these counts. [Training code](../src/skylens/train.py) · [Split audit](airport_serving_eligibility_audit.md)

The 592 eligible research profiles each have at least 50 fitting rows for the exact route, airline label, cabin and stop count. Individual research requests also have to satisfy the historical numeric input bounds. Both models predict source-recorded values with unresolved currency, tax, fee, passenger and booking semantics. Customer ML eligibility remains false across the inventory. [Target review](price_target_reaudit_20261115.md) · [Approval decision](../data/metadata/phase5/acquisition_decision.json)

A route marked `unprobed` has unknown provider availability, observation count and currency. No estimation method has been evaluated for it. A route marked `see_dated_requests` has evidence for the recorded queries only. A change in date, party, cabin, journey, airline filter or retrieval time can change the result. Neither directory membership nor an earlier result establishes current service or fare availability.

| Market outcome in a dated request | Interpretation |
| --- | --- |
| `observed` | The estimator selected a comparable INR group. The count records the observations used for that search. |
| `no_usable_observations` | The completed search supplied zero usable observations. The source status distinguishes an empty result from incompatible evidence. |
| `technical_failure` | The provider check failed. The source status records the error, such as timeout, quota or invalid response. Comparable observation count is unknown. |
| `unconfigured`, `unsupported_request`, `not_requested` | The requested source was unconfigured, outside its declared request support, or unused. Comparable observation count is unknown. |

An empty count in the CSV means unknown. Zero means that a completed search yielded zero comparable observations. An unavailable estimate has an empty output currency. Without documented evidence of the observed currency, compatibility is recorded as unknown.
