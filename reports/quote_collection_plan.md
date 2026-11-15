# Repeatable quote-collection experiment

Status: preregistered design, **not executed**. No source has a recorded collection/storage/ML grant. Begin only after the [access audit](quote_source_access_audit.md) dependencies are resolved. No paid calls or tickets are part of this design.

## Route selection from actual evidence

The historical directory has 661 airfields, 165 IATA codes, 88 observed fare endpoints and seven research-eligible airports: AMD, BLR, BOM, CCU, DEL, HYD, MAA. The following 12 directional routes are present in actual historical files. Seven form a cycle covering all eligible airports. Five extension routes add western, northeastern, southern, island and northern observations without claiming service or serving eligibility. Historical network/challenge observations remain distinct; neither establishes current schedules or verified prices.

| route | cabin_2023_rows_excluding_First | network_2020_rows | later_challenge_rows | stratum |
| --- | --- | --- | --- | --- |
| DEL-BOM | 19085 | 0 | 0 | both eligible historically |
| BOM-BLR | 15629 | 0 | 0 | both eligible historically |
| BLR-HYD | 12317 | 62 | 71 | both eligible historically |
| HYD-MAA | 9242 | 43 | 80 | both eligible historically |
| MAA-CCU | 7980 | 0 | 0 | both eligible historically |
| CCU-AMD | 4580 | 0 | 0 | both eligible historically |
| AMD-DEL | 8877 | 50 | 68 | both eligible historically |
| BOM-PNQ | 0 | 54 | 66 | extension research only |
| DEL-GAU | 0 | 32 | 63 | extension research only |
| BLR-COK | 0 | 63 | 85 | extension research only |
| DEL-IXZ | 0 | 43 | 42 | extension research only |
| DEL-JAI | 0 | 19 | 25 | extension research only |

## Sampling unit and repeatable schedule

An itinerary is a fixed set of flight segments on actual departure/return dates, with cabin, fare family, baggage/refund conditions and passenger composition held constant for comparisons. A snapshot is one source offer at one query instant. A collection day is its India-local calendar date. Shared segments connect dependent observations even across different cabins, sources and genuine return products. Same-day refreshes remain history, not extra independent samples.

After permission, make a route/carrier availability inventory using the authorized interface. Record no-service/unavailable/permission-denied outcomes without inventing prices or silently substituting another route/carrier. Historical GO FIRST/Vistara labels do not establish current services. Select actual available carriers, aiming for two distinct marketing carriers per route where authorized availability permits, and distinguish operating carriers. Start with a single adult, no loyalty/corporate/student discounts, fixed market/currency and explicit mandatory fees. Preserve promotion/fare-family/baggage differences; compare matched products only.

A logistics pilot selects four distinct departure dates per route (two weekdays, two weekend dates) across at least four collection weeks: up to 48 route/departure cells before carrier/class expansion. Rotate early (05:00–11:59), midday (12:00–17:59) and evening (18:00–23:59) **departure** periods across dates. Collect at a fixed 10:00 IST session, with actual timestamp recorded and randomized route order; a missed session is missing data. This pilot size is a balanced workload allocation, **not** a sufficient ML sample or a precision claim.

Anchor each fixed itinerary at 35 days before departure where visible. Repeat its authorized offer at leads 28, 21, 14, 7, 3 and 1 days, retaining the same segments/product. Add rolling departure cohorts to observe several leads on the same collection date; this helps separate lead-time effects from calendar shocks. Include multiple collection weekdays over at least four weeks for the pilot; expand the day span based on estimated date correlation. A collection date can induce common shocks, so different dates are not assumed statistically independent simply because they differ.

Economy is the starting cohort. Add actual Business/Premium Economy cells only when the route/carrier sells them with permission; log absence, never map a fare brand to a cabin by guess. First remains outside the current model. A separate return arm uses a **single actual return offer** with fixed outbound/inbound flights and stay length. Pair it with separately recorded compatible outbound/inbound one-way offers only if all three products and total semantics are independently evidenced. Do not create return targets by addition. Journey types remain separate target strata.

Apply the source's daily limits to **all raw observations**, including refreshes and malformed entries, and stop rather than circumvent a rate/access gate. Keep a private session log with planned cell, actual timestamp, result status and reason; unavailable results are not zero-price observations. No external collector runs automatically.

## Statistical stopping and validation budget

Set precision and practically meaningful improvement before seeing the final test. For an overall interval-coverage proportion, approximate 95% precision of ±5 percentage points requires `ceil(1.96² × p(1-p) / 0.05²)`: **139 independent test units** if p=0.9 is an adequate planning estimate, or **385** using conservative p=0.5. Use Wilson/exact binomial intervals when reporting actual coverage, not the approximation as a guarantee. These are overall evaluation-planning numbers, not training minima or a rule that 385 snapshots validate every airport. Each claimed subgroup needs its own justified precision and multiplicity treatment. [NIST sample-size guidance](https://www.itl.nist.gov/div898/handbook/ppc/section3/ppc333.htm), [binomial confidence limits](https://www.itl.nist.gov/div898/handbook/prc/section2/prc241.htm).

For mean absolute error, use pilot cluster-level error variability `s` and a preregistered absolute tolerance `delta`: planning `n ≈ (1.96*s/delta)²`. Neither `s` nor an INR improvement threshold can be estimated from zero quotes or from legacy source units. For repeat measurements, estimate itinerary/day correlation and use itinerary and collection-day block bootstrap or multiway clustering; a simple balanced-cluster approximation is `DEFF = 1+(m-1)*rho`. Do not plug in an invented correlation or treat repeated refreshes as n. Expand the number of distinct itineraries/days until uncertainty and intended subgroup coverage are adequate. Sparse strata remain unsupported.

Use separate chronological training, tuning-validation, calibration and final-test windows chosen before final targets are opened. Collect fresh itinerary cohorts in every window; shared-segment components spanning windows are purged by the split tool. Keep the final test sealed from feature/hyperparameter/threshold selection and never calibrate on it. Need counts **after** purging, not raw counts. The initial 48-cell logistics pilot cannot fulfill the independent final-test plan, calibration requirement or nationwide coverage. If feasible zero-cost authorized access cannot meet this design, report insufficient evidence and retain the existing models.
