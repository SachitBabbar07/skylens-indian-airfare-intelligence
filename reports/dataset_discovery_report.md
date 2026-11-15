# Dataset discovery
Research: 14–15 November 2026, Asia/Kolkata. This is a bounded search, not a claim to enumerate every possible dataset.

Kaggle's public catalog yielded 47 distinct references across Indian flight price, India airfare, flight fare, round trip and domestic-flight searches. Original cards/search snapshots are in data/metadata. Hugging Face broad searches were supplemented by specific schedule, fare-history and return-quote cards. Web searches also covered GitHub, Zenodo, Figshare, OpenML, government sources and academic studies. No additional qualified Indian domestic return-fare file was located; this does not prove none exists.

Eight original free public Kaggle source archives and a commit-pinned OurAirports snapshot were downloaded without credentials. dataset_registry.json and file_profiles.json contain actual byte sizes, hashes, rows, schemas, dtypes, missing counts and samples. No paid API, live booking-site scraping, authentication bypass or restricted download was used.

Important file findings:
- The 2023 cabin raw source has 452,088 rows, seven cities and four cabin labels. All booking dates are 15 January 2023: 50 departure days are not 50 collection days. First has only 144 rows and is excluded from modeling.
- The pre-pandemic PromptCloud sample has 30,024 rows, with 14,877 domestic records retained across 88 airports and 679 directional routes. It has only three collection days. The later sample actually has one collection day and departures 16–27 April, narrower than its advertised April–June range.
- The Goibibo file has 300,261 identical ordered flight IDs versus the 2022 raw files, and every date shifts by 500 days. 68.1610% of prices equal rounded original × 1.01. It cannot establish independent 2023 validation.
- The broad 2019–2025 candidate uses route tokens such as MUM/PUN/BAN and inconsistent clock/duration fields without collection evidence. Authenticity is unverified; it is not asserted to be proven synthetic.

Selected sources have no verified currency, tax inclusion, passenger basis or booking journey type. They remain category G research datasets, with currency and normalized_price_inr missing. Single-direction rows are not automatically genuine one-way bookings. No reverse routes are combined into return fares. ATL international returns are out of scope. Schedule, airport, traffic and aggregate datasets are classified separately.

| source | category | license | decision |
| --- | --- | --- | --- |
| andrewgeorgeissac/flight-price-data-of-indian-cities-makemytrip | G | Community Data License Agreement - Sharing - Version 1.0 | Separate base-fare sample explicitly excluding taxes; missing dates/class/passenger basis. |
| iamavyukt/goibibo-flight-data | G | CC BY-NC-SA 4.0 | Rejected: derivative ordered flight records with 500-day date shift; not independent validation. |
| nikhilmittal/flight-fare-prediction-mh | G | Unknown | Not downloaded: original license unknown; a mirror does not resolve original rights. |
| orhfusion/flight-price-dataset | G | Apache 2.0 | Unverified price scope/provenance; not selected. |
| promptcloud/easemytrip-flight-fare-details-2020 | G | CC0: Public Domain | Selected separate domestic research cohort or later drift challenge; missing class/price definitions. |
| promptcloud/easemytrip-flight-fare-travel-listings | G | CC0: Public Domain | Selected separate domestic research cohort or later drift challenge; missing class/price definitions. |
| shraddha4ever20/indian-domestic-flights-dataset-20192025 | G | Attribution 4.0 International (CC BY 4.0) | Rejected: collection authenticity unverified; pseudo airport codes and inconsistent clock/duration fields. |
| shubhambathwal/flight-price-prediction | G | CC0: Public Domain | Reference only: fewer cities and weaker collection lineage; not appended to inflate records. |
| sumitjaiswar/indian-domestic-flights-data | E | MIT | No price column; traffic/network sample with insufficient collection provenance. |
| yashdharme36/airfare-ml-predicting-flight-fares | G | CC0: Public Domain | Selected isolated cabin research; one collection day and unknown standardized target. |
| OurAirports | C | Public domain | Selected commit-pinned airport/region metadata, not fare evidence. |
| HF IndianDomesticAirlineDataset mirror family | G | Original unknown | Schedules only. THULab conversion says defer to unknown original rights. Not ingested. |
| India Cheap Flights index | F | CC BY 4.0 stated | Aggregated usual fares/ranges, not individual quotes. Not ingested. |
| Piratefly fare history | F | Custom Travelpayouts-derived terms | EUR aggregates with underlying redistribution restrictions. Not ingested. |
| ATL international return quotes | G | MIT card | Genuine returns described, but ATL international; not Indian domestic. Advertised 3.85 GB not downloaded. |
| Vonter DGCA traffic | E | ODbL 1.0 | Passenger/freight network data, no quoted prices. Not ingested. |
| IIMA Dutta and Santra 2015 | G | Raw reuse rights not found | 2012 one-way minima described in paper; reusable raw supplement not located. |
| OpenSky Zenodo movement data | E | See source LICENSE.txt | Aircraft movements, not fares; no download needed for target. |
| Avij112 fare analysis | G | Not established for raw fares | Repository describes interpolation; interpolated prices excluded. |
| Dhairya Flights-Dataset | G | No explicit data license found | Aertrip non-stop economy source, six airports claimed; not downloaded without clear reuse rights. |
| OpenFlights routes | E | ODbL/DbCL reported, unverified here | Historical routes, not prices. Not ingested. |

Mirrors and raw/cleaned representations are one source family. Inaccessible or unlicensed candidates remain unverified rather than silently used.
