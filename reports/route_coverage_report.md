# Airport and route coverage
| concept | actual_count |
| --- | --- |
| indian_airfield_records | 661 |
| with_iata | 165 |
| scheduled_flag | 120 |
| fare_airports | 88 |
| fare_origins | 66 |
| fare_destinations | 82 |
| fare_routes | 720 |
| production_eligible_airports | 0 |
| without_fare_evidence | 573 |

661 master records include heliports, closed and noncommercial airfields. They are not 661 passenger airports. The 120 scheduled flags come from OurAirports, not independent current-service verification. No separate schedule source is ingested. The master includes source commit/date, state, coordinates and status caveats; district information is unavailable and not invented.

The selected observations span 88 historical airports, 66 origins, 82 destinations and 720 directional routes across primary and later challenge cohorts. The pre-pandemic candidate alone has 679 routes; external-only data do not expand serving eligibility. There are 573 master records without selected fare evidence.

Cabin research: 592 eligible exact profiles across seven airports and 42 routes. Network: maximum exact training profile 17, so zero eligible profiles. Verified production-eligible airports: zero. The minimum 50 observations per route × airline × class × stops is a conservative research operational heuristic, not a reliability theorem. Observed numeric ranges also gate requests. It was not lowered after discovering sparsity. New airports and routes remain blocked despite coordinates.

See india_airport_master.csv, airport_fare_coverage.csv, route_fare_coverage.csv, data/metadata/city_airport_mapping.csv and models/COHORT/support.csv. Current passenger/commercial operations require authoritative independent evidence. Fare observations, metadata, schedule flags and supported predictions remain separate concepts.
<!-- SKYLENS_PHASE2_START -->
## Phase-two correction — 15 November 2026

The original report above records phase-one results. Phase-two inspection
confirmed its numeric metrics but found zero cabin final-test rows inside the
current numeric serving domain (fit lead days 1–35, test 41–50). The old aggregate
interval gate is no longer used: API intervals are withheld. Seven clock-float
boundary rejections were fixed; genuine out-of-range values remain rejected.
Training data/model artifacts, the 50-row rule and the 88-observed/7-research/
0-production airport counts remain unchanged. See model_reliability_phase2.md,
airport_serving_eligibility_audit.md and browser_and_end_to_end_qa.md.
<!-- SKYLENS_PHASE2_END -->
