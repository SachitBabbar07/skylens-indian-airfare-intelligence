# Original target documentation re-audit — 15 November 2026

**No reviewed original documentation establishes the monetary meaning needed for customer fare prediction.** Currency remains null; no INR relabelling, guessed exchange rate, conversion, tax adjustment or synthetic target was introduced. This describes the materials reviewed, not every document that might exist elsewhere.

## Materials reviewed again

Original publisher descriptions were fetched again from Kaggle's public metadata API on 15 November 2026: HTTP 200, version 1 for all three. Full descriptions, frozen raw/cleaned headers, acquisition records and preparation/target code were reviewed. URLs, timestamps and response hashes are in [source retrievals](../data/metadata/product_correction/source_retrievals.json). Full third-party descriptions remain local and ignored.

| Original source | Established by reviewed documentation | Still undocumented |
| --- | --- | --- |
| [Yash Dharme: Airfare ML](https://www.kaggle.com/datasets/yashdharme36/airfare-ml-predicting-flight-fares), cabin model | Describes EaseMyTrip scraping, dates, itinerary/class fields and Price. Frozen raw `Price` and cleaned `Fare` headers are present. | Currency, tax/fee inclusion, total versus base fare, passenger basis and genuine booking type. No target-semantics dictionary identified. |
| [PromptCloud: Fare Details 2020](https://www.kaggle.com/datasets/promptcloud/easemytrip-flight-fare-details-2020), network model | Describes an EaseMyTrip sample, collection window and itinerary fields including Fare. | The same monetary and booking definitions. Naming a field Fare does not define its meaning. |
| [PromptCloud: Travel Listings](https://www.kaggle.com/datasets/promptcloud/easemytrip-flight-fare-travel-listings), external challenge only | Describes a separate later sample, itinerary fields and Fare. | The same definitions; no verified compatible target for promotion or retraining. |

Linked [DataStock Fare Details](https://app.datastock.shop/?site_name=EaseMyTrip_Flight_Fares_Dataset) and [Travel Listings](https://app.datastock.shop/?site_name=EaseMyTrip_Flight_Fare_Travel_Listings_) catalogues were not readable through the web tool, which reported each URL not accessible. No additional dictionary or price definition could be verified there. No paid access, authentication workaround or publisher contact was attempted. Current booking-site conventions cannot establish historical exported-field semantics.

## Unresolved definitions

| Required definition | Cabin source | Network source | Consequence |
| --- | --- | --- | --- |
| Currency/denomination | Undocumented | Undocumented | Cannot label or convert to INR |
| Taxes and mandatory fees included? | Unknown | Unknown | Cannot assert an all-in total |
| Total fare versus base fare? | Unknown | Unknown | Cannot advertise a customer fare |
| Per passenger versus entire booking? | Unknown | Unknown | Cannot interpret a passenger price |
| One-way, return or other booking? | Single-direction record only | Single-direction record only | Cannot claim a verified booking type |
| Documentation validating these meanings? | Not identified | Not identified | Customer mode stays disabled |
| Independent validation for intended serving scope? | Not established | Not established | Semantics alone would still be insufficient |

Indian routes, plausible magnitudes and Price/Fare field names do not prove INR or total fare. Preparation parses numerical source values, checks the raw/cleaned cabin representation match, keeps currency unknown and leaves `normalized_price_inr` missing. The fitted target is a historical **numerical source field with unverified semantics**.

## Why 54,757 appeared

The previous default was AMD→BLR, Air India, Business, one stop, one lead day, 335 minutes, departure 07:55. The unchanged model outputs approximately **54,757.14**; the old large card rounded that to **54,757** and labelled it “Estimated recorded fare”. Business class and lead-time contributions explain part of the numerical result but do not establish its monetary validity.

It is neither a collected quote nor a verified INR ticket price. Its native SHAP baseline is approximately 22,917.85 in the same unverified units; thirteen contributions sum to the output within 1e-8. High offline R² cannot repair missing definitions or establish accuracy for current customer inputs.

Before a customer release, obtain authoritative source-specific definitions tied to actual records for currency, taxes/fees, total/base scope, passenger basis and genuine journey type. Establish a compatible, permitted target and independently evaluate representative real quotes over intended routes, dates, cabins and query-time scope, including error and uncertainty. Review this evidence before implementing an approved serving capability. An INR metadata edit, disclaimer or plausible number is insufficient.

The [correction report](product_correction_20261115.md) records implementation and verification. No dataset, model or training pipeline changed.
