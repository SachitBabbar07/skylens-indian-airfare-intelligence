# Market fare estimation and accuracy evaluation

## Delhi–Chandigarh discrepancy

The reported ₹6,807–₹8,293.50 band cannot be the quartiles of ₹6,200, ₹6,300 and ₹6,400. With those three values alone, the previous interpolation gives ₹6,250 and ₹6,350. The original provider response and its retrieval time were not retained. That prevents exact reconstruction of the user's original request and verification of the display, discounts and tax treatment of those three offers.

On 19 November 2026 we captured a fresh search for 26 November, DEL → IXC, one way, one adult, Economy, any airline. We ran the previous and revised calculations on the **same observations** to isolate the effect of the algorithm.

| Calculation | Observations | Result in INR for the party |
| --- | ---: | --- |
| Previous estimator | 15 flights, all stop counts combined | Q1 ₹6,925, median ₹12,508, Q3 ₹19,672 |
| Revised estimator | 7 nonstop flights, 50–70 minutes | Median ₹6,830. Sample too small for a band. |
| Connections excluded from the nonstop group | 8 one-stop flights, 340–495 minutes | Observed prices ₹11,475–₹22,298 |

The normalized nonstop observations, in price order, were ₹6,461, ₹6,738, ₹6,754, ₹6,830, ₹7,020, ₹7,233 and ₹12,508. Every eligible flight contributed once. The most expensive nonstop remained in the calculation. On 22 November, a separate lookup through the production browser showed ₹7,308 from seven nonstop flights for the same travel date. Changes between retrievals reflect different source observations. The dated comparison above holds the input fixed. [Dated probe results](market_probe_results.json)

### From the provider to the screen

The form sends airport codes, exact dates, journey, cabin, airline preference and adult/child/infant counts to FastAPI. The Kiwi adapter reads structured numerical itinerary prices, checks the returned INR and echoed passenger composition, and verifies domestic segments, airline filters, cabin, chronology, direction and local dates. The connector documents whole-party prices. Tax and fee inclusion is unknown. There is no exchange-rate conversion, passenger multiplication, fee adjustment, discount or route calibration. React formats the returned decimal values using Indian currency formatting. [Provider scope](https://www.kiwi.com/stories/kiwi-mcp-connector/) · [Source adapter](../backend/app/kiwi_fares.py) · [Selector](../backend/app/hybrid_estimator.py)

The old selector combined different stop counts within the same monetary group. The revised selector keeps itineraries with the same stops in each direction, deduplicates known schedules and flight identities, and uses compatible price terms. It selects the fewest observed connections without consulting the prices. If no single round trip satisfies both directional minima, the market result is unavailable. A route served only by connections can still produce an explicitly labelled connecting reference. Durations are checked against the timestamps and summarized per direction.

For eight or more distinct comparable itineraries, SkyLens reports the median and the linearly interpolated 25th and 75th percentiles. Eight is a reporting threshold chosen to give at least two observations per quarter. It is not a measured accuracy threshold. For smaller groups the API returns a median, null bounds and a limited-sample qualification. The 1.5-IQR rule flags potential outliers for review when quartiles are reported. A valid fare retains its weight even when flagged. The Kiwi tool advertises price as its default result ordering. Its returned sample can omit other available fares and is not a random sample of airline inventory. [Statistical method](https://www.itl.nist.gov/div898/handbook/eda/section3/boxplot.htm) · [API contract](../docs/API_GUIDE.md#flight-search)

## Performance evidence

Nine live market lookups on 19 November covered eight directed routes, multiple departure dates, different party sizes and both journey types. They produced three interquartile bands, five limited-sample references and one empty result. The public record contains aggregate results for the tested itineraries. The complete route inventory distinguishes unprobed routes from completed empty checks. [Coverage and dated requests](market_coverage.md)

| Route group | Searches | Independent comparable outcomes scored |
| --- | ---: | ---: |
| Metro to metro | 2 | 0 |
| Metro to regional | 3 | 0 |
| Regional to metro | 1 | 0 |
| Regional to regional | 3 | 0 |

The verified quote intake contains zero independent ticket-price targets. Eight references also have unknown tax and fee inclusion, and one search yielded no estimate. Consequently customer INR MAE, RMSE, signed bias, median absolute error, MAPE and empirical band coverage are **unmeasured** overall and in every route group. A route-level promotional minimum or a published tariff schedule does not establish a contemporaneous, selectable itinerary total with matching terms. The user's three example prices were excluded from fitting and scoring. [Air India route page](https://www.airindia.com/en-in/book-flights/delhi-to-chandigarh-flights) · [Quote admission](../docs/QUOTE_COLLECTION_GUIDE.md)

We independently replayed the original CatBoost feature builder, saved artifacts and held-out partitions. Artifact and dataset hashes, feature order, split sizes and archived predictions matched. These errors are in **source units**, with positive bias meaning overprediction.

| Research model | Held-out rows | MAE | RMSE | Signed bias | Median absolute error | MAPE | Historical interval coverage |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| Cabin 2023 | 88,773 | 2,339.76 | 4,376.35 | +266.70 | 998.19 | 13.71% | 89.24% |
| Network 2020 | 5,445 | 2,764.66 | 4,664.68 | −570.09 | 1,583.13 | 23.08% | 85.16% |

Neither holdout contains observations within the corresponding current serving gates. Currency, passenger basis and price scope remain unresolved. Both saved models continue in Research Mode. No supervised price model or learned blending weights are approved for customer INR output. The selector uses an approved model first when its declared scope matches. Only known, matching stop profiles and monetary terms allow comparison with a market reference. [Model audit](supervised_fare_status.md)

## Application checks on 22 November 2026

All 295 Python tests and 24 frontend tests passed. The production TypeScript and Vite build succeeded. The Python run emitted two dependency deprecation warnings from the test client.

The production Flights page displayed a single ₹7,308 whole-party reference for DEL → IXC on 26 November, with the nonstop label, seven-itinerary sample size and unknown tax and fee treatment. The result remained readable at a 390-pixel mobile viewport without horizontal overflow. Browser QA found no console warnings or errors. Replaying the nine saved searches offline reproduced the public aggregate results.

## Reproduction

From the project root, the following commands replay the 19 November observations on the submission machine and export coverage. The full coverage export also works from the public repository alone. Private observations are excluded from Git and from training.

```powershell
$env:PYTHONPATH = 'src'
.\.venv\Scripts\python.exe -m scripts.probe_market_fares summarize --directory data/cache/market-probes/2026-11-19 --report reports/market_probe_results.json
.\.venv\Scripts\python.exe scripts/build_market_coverage.py
.\.venv\Scripts\python.exe -m skylens.evaluate_market --captures data/cache/market-probes/2026-11-19/estimates.jsonl
.\.venv\Scripts\python.exe -m skylens.evaluate_market_history
```

For a fresh authorized provider check, use `python -m scripts.probe_market_fares capture --first-departure YYYY-MM-DD --directory data/cache/market-probes/RUN` with a future date and a new private directory. Calls are sequential. The capture tool skips existing requests and halts on quota, rate-limit, authentication or certificate failures.

For a future independent evaluation, add `--split PATH --independent-pairs PATH` to the evaluator. The first file is the quote intake's frozen chronological split. The second is a private JSON list with `provider`, `independent_source_id`, `reviewed_by`, `evidence_reference` and `evidence_sha256` per reviewed source pair. The evaluator validates the evidence, checks the capture against the estimator, and matches a later independently observed selectable all-in INR total within 15 minutes of the inputs. It requires identical cabin, party, dates, flight numbers, carriers and segment times. Shared legs are excluded across samples and the holdout boundary. The current independent matching implementation supports nonstop legs, including nonstop round trips. Empirical band coverage is withheld below 20 scored bands. This is a reporting rule, not a confidence guarantee. [Evaluator](../src/skylens/evaluate_market.py)
