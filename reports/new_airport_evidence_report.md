# Airport evidence after Phase 3

**No airport changed eligibility.** Verified new observations: 0. Historical fare endpoints: 88. Research-eligible endpoints: AMD, BLR, BOM, CCU, DEL, HYD, MAA. Production-eligible endpoints: 0.

[new_airport_evidence.csv](new_airport_evidence.csv) records every one of the 661 directory records, including airfields with no IATA code or fare evidence. It carries previous endpoint observation counts, directional routes, airline/cabin labels, collection/travel coverage, historical quote-group proxies, new verified observations/itineraries/routes/carriers/classes/days, currency/price definition, statistical support and the unchanged decision. No previous rows are reclassified as verified INR targets.

True historical unique booking-itinerary counts are not established by undocumented single-direction rows; their quote-group proxy is explicitly separate. New verified itinerary count and total **verified** itinerary count are both zero. Adding endpoint observations across incompatible source cohorts would not yield a valid independent sample size.

The exact `(origin,destination,airline,cabin_class,stops)` fitting-support threshold remains 50, with existing per-cell numeric bounds. It is an operational safeguard, not proof of statistical reliability. New airport support would need source-semantic compatibility, distinct itineraries and dates, profile coverage and independent subgroup validation. More airport metadata or repeated refreshes cannot supply that evidence. No threshold reduction, automatic training ingestion or new serving option was made.
