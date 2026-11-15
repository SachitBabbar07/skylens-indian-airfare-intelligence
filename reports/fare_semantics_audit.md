# Fare semantics audit — 15 November 2026

| cohort | target | currency | taxes_fees | passenger_basis | booking_journey_type | cabin_labels | collection_days | travel_dates | collection_status |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| cabin_2023 | source-recorded listing fare | unknown | unknown | unknown | unknown; directional record only | Business, Economy, Premium Economy | 1 | 2023-01-16 to 2023-03-06 | single static query snapshot |
| network_2020 | source-recorded listing fare | unknown | unknown | unknown | unknown; directional record only | Unspecified | 3 | 2020-01-02 to 2020-02-29 | static sample of timestamped crawls |
| network_external_2020 | source-recorded listing fare | unknown | unknown | unknown | unknown; directional record only | Unspecified | 1 | 2020-04-16 to 2020-04-27 | static sample of timestamped crawls |

## What the number represents

The publisher describes scraped flight listings, not verified completed purchases.
The strongest description for the selected target is a **source-recorded listing
fare with undocumented price scope**. It cannot be advertised as a tax-inclusive
total, base fare, price per adult, full booking total or segment price. Even if INR
were independently established, these remaining questions would stay unresolved.
No division/multiplication by passenger count or summing reverse fares is valid.

The 2023 raw Airline-Class field contains actual Economy, Premium Economy,
Business and First labels. The source labels are preserved rather than inferred
from price; the 144 First rows remain excluded from fitting/serving. PromptCloud
does not record cabin, so Unspecified is a representation of missing information,
not a fourth verified cabin. Neither source records return settings, a priced
return itinerary or return dates. A directional itinerary is not proof of the
booking journey type.

## Time is not a transaction receipt

The 2023 Date of Booking field is 15 January 2023 for every raw row. Departure
dates are 16 January–6 March; arithmetic lead time is valid relative to that
source field, but does not prove an actual purchase occurred. There are no
independent changing query days. PromptCloud crawl timestamps provide three
January/February collection days and one April collection day after conversion
to Asia/Kolkata. They are observation times, not actual passenger booking times.
The advertised quarter is not substituted for the narrower dates in the files.

Canonical travel/collection dates, actual cabin labels and lead-time arithmetic
are documented in data/metadata/phase2/fare_semantics.json. Raw bytes and model
training targets were not edited.

## Potential alternatives

MakeMyTrip explicitly documents a base fare excluding taxes but lacks needed quote
settings/dates/class information. The 2019 mirror family documents INR in two
cards, without verified passenger, tax, booking or cabin scope. The 6,062-row
cleaned SSHRIYA source has booking dates but no cabin/currency documentation;
added Booking_Hour/Booking_DateTime provenance is not explained. Those hours
must not become authentic timestamps by assumption. Its five city labels do not
establish new airports beyond the existing 88. Synthetic Air India prices and
aggregate indices remain separate categories.

## Target decision, made before diagnostic fitting

See prediction_target_decision.md. Keep current research targets isolated and
retain the trained models. A future product target needs a documented currency,
total/tax/fee scope, adult-passenger basis, genuine journey type, cabin, query
time and departure date under usable source rights. Genuine returns need their
actual total and return date. No full retraining or currency relabeling is
justified by the current evidence.
