# Fare currency audit — 15 November 2026

The three selected cohorts still have **unknown currency**. This conclusion is
source-specific: original publisher descriptions were fetched again through the
public Kaggle API, public file-list metadata was inspected, and the untouched raw
price fields were checked. No separate record currency or explicit default was
found. Commas in a number, domestic geography, or today's EaseMyTrip defaults do
not establish the historic extraction currency.

| cohort | publisher | price_field | record_currency_field | original_documented_default | mixed_currency_test | decision | card |
| --- | --- | --- | --- | --- | --- | --- | --- |
| cabin_2023 | Yash Dharme | Price | absent | not found | not possible from records | Case C: unknown; no INR normalization | https://www.kaggle.com/datasets/yashdharme36/airfare-ml-predicting-flight-fares |
| network_2020 | PromptCloud | Fare | absent | not found | not possible from records | Case C: unknown; no INR normalization | https://www.kaggle.com/datasets/promptcloud/easemytrip-flight-fare-details-2020 |
| network_external_2020 | PromptCloud | Fare | absent | not found | not possible from records | Case C: unknown; no INR normalization | https://www.kaggle.com/datasets/promptcloud/easemytrip-flight-fare-travel-listings |

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
