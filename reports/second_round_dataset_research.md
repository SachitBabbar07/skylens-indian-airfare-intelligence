# Second-round dataset research

Bounded search performed 15 November 2026. Seven public Kaggle queries returned
32 distinct references; Hugging Face searches, GitHub source trees,
and web searches targeting Zenodo, Figshare, OpenML, government, official/academic
sources were also reviewed. No qualifying additional Indian domestic return-price
file or compatible verified total-per-passenger dataset was found. This is not a
claim that all internet datasets were exhausted.

Four new publicly licensed distributions were downloaded into data/raw/phase2,
with immutable archives, extracted-file hashes, actual schemas/missingness/samples,
and audit-only entries in the main registry. None enters training or coverage.
The bundled 83,259-row airport file is metadata, lacks an IATA column in this
distribution and does not expand fare evidence.

| candidate | category | downloaded | actual_files | license_declared | source | decision |
| --- | --- | --- | --- | --- | --- | --- |
| viveksharmar/flight-price-data | G: audit only | True | flight_dataset.csv: 10,683 rows | MIT | https://www.kaggle.com/datasets/viveksharmar/flight-price-data | 2019 derivative; undocumented currency/quote settings. |
| ankushsonar/flight-price-dataset-india-2019 | G: audit only | True | Flight_data.csv: 10,683 rows | CC0: Public Domain | https://www.kaggle.com/datasets/ankushsonar/flight-price-dataset-india-2019 | Publisher-declared INR; same ordered 2019 keys, unclear upstream lineage and malformed arrival date. |
| prithvirajshukla/flight-fare-prediction | G: audit only | True | Flight_Fare.xlsx: 10,683 rows | MIT | https://www.kaggle.com/datasets/prithvirajshukla/flight-fare-prediction | Publisher-declared INR; same 2019 family, no passenger/tax/booking scope; provenance claim unverified. |
| sshriya08/flight-price-prediction-dataset | G: audit only | True | airports.csv: 83,259 rows; flight_cleaned.csv: 6,062 rows | Attribution 4.0 International (CC BY 4.0) | https://www.kaggle.com/datasets/sshriya08/flight-price-prediction-dataset | No documented currency/cabin or added booking-hour provenance; source lineage unresolved. |
| Air India revenue management 1m | synthetic | False | not downloaded | CC0 | https://www.kaggle.com/datasets/aryansingh2000/air-india-revenue-management | Original card explicitly describes simulated/synthetic data. Not downloaded or trained. |
| Air India revenue management 50m | synthetic | False | not downloaded | CC0 | https://www.kaggle.com/datasets/aryansingh2000/air-india-revenue-management-data-analytics | Explicitly synthetic; advertised scale is not authentic fare evidence. |
| Mohit Tomar raw fare source | G | False | not downloaded | Unknown | https://www.kaggle.com/datasets/mohittomar2008/flight-price-prediction-through-webscrapping | Card inspected; original reuse rights and currency unestablished. No restricted file acquisition. |
| SIH India airfare index | G: demo | False | not downloaded | No repository license found | https://github.com/keyholder1/sih-india-airfare-price-index | Example generator explicitly fabricates prices; no real fare CSV in inspected data tree. Not trained. |
| TOI-DPA index | F | False | not downloaded | Raw reuse terms not established | https://www.decimalpointanalytics.com/what-we-do/data-science-and-ai/toi-dpa-airline-price-index | 56-route descriptive economy index; no accessible licensed itinerary microdata established. |
| India Cheap Flights index | F | False | not downloaded | CC BY 4.0 stated | https://indiacheapflights.com/press/ | Aggregated usual fares/ranges. Raw JSON request returned 403; no bypass or file-content claim. |
| Piratefly fare history | F | False | not downloaded | Custom Travelpayouts-derived terms | https://huggingface.co/datasets/DeusHorizon/flight-fare-history | Explicit EUR one-way aggregates, not compatible itinerary observations. |
| Flight Price Observatory | out of geography | False | not downloaded | Apache-2.0 code; underlying data rights not established here | https://github.com/notlega/flight-price-observatory | Documents SGD and SIN foreign routes/returns; no Indian domestic coverage in described catalog. |
| MoSPI CPI collection methodology | methodology | False | not downloaded | Not an observation dataset | https://www.mospi.gov.in/uploads/documents/documents/1769670534541-Export_report_CPI.pdf | Useful one-adult one-way economy collection definition; no downloadable individual fare observations found. |

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
