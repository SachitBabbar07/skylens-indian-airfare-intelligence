# Airport serving eligibility audit

The original 88 observed airports and seven research-eligible airports are
reproduced from the actual data. There are **81 research-ineligible observed
airports and zero verified production-eligible airports**. All seven eligible
airports are AMD, BLR, BOM, CCU, DEL, HYD and MAA.

The companion airport_serving_eligibility_audit.csv contains **one row per observed
airport** with endpoint counts, directional routes, airline/operator labels,
classes, journey/currency/scope status, collection/travel span, missingness, quote
groups, per-model fitting observations and exact ineligibility reasons.

The wide 2020 source has 14,877 retained domestic rows before splitting, with
7,028 final fitting rows. It is fragmented into 2,401 route × carrier-label ×
class × stop cells; the largest has only 17 fitting rows. No network cell passes
50. Carrier combinations are retained as original labels, not invented single
airlines. The later 22,735-row challenge never contributes fitting support.

The cabin source has 445,366 deduplicated observations, including 144 rare First
rows excluded from modeling. Train+validation fit 311,968 rows and provide 592
eligible exact cells across its seven airports. Sources with missing cabins or
uncertain price definitions cannot simply be appended to fill sparse cells.

## Missingness and independence

Core retained numeric/categorical inputs have no nulls after documented filters.
That is not complete semantics: currency and price scope are undocumented for
100% of selected observations; network cabin is Unspecified. Distinct quote
fingerprints eliminate exact duplicates but do not establish statistical
independence. Shared flights, routes and collection days induce dependence.
Cabin's single collection day and network's three fitting-candidate days are
especially limiting; counts are observations, not independent booking events.

## Threshold review

Fifty is an operational research heuristic, **not statistically established
reliability**. The following new experiment fits training only and measures the
unchanged validation partition with 250-tree diagnostic models. It does not use
the final test or change serving eligibility. Counts here use training-only
support; the deployed support CSV includes the final train+validation fit, so
579 diagnostic cabin cells at threshold 50 are not a contradiction of 592 served
cells.

| cohort | minimum_profile_count | fitting_airports | eligible_profiles | validation_rows | mae |
| --- | --- | --- | --- | --- | --- |
| network_2020 | 5 | 50 | 240 | 420 | 2216.375 |
| network_2020 | 10 | 8 | 5 | 11 | 1129.574 |
| network_2020 | 20 | 0 | 0 | 0 | not established |
| network_2020 | 50 | 0 | 0 | 0 | not established |
| network_2020 | 100 | 0 | 0 | 0 | not established |
| network_2020 | 200 | 0 | 0 | 0 | not established |
| cabin_2023 | 5 | 7 | 737 | 44670 | 2736.557 |
| cabin_2023 | 10 | 7 | 723 | 44663 | 2736.192 |
| cabin_2023 | 20 | 7 | 681 | 44552 | 2735.583 |
| cabin_2023 | 50 | 7 | 579 | 44023 | 2746.212 |
| cabin_2023 | 100 | 7 | 467 | 42636 | 2768.105 |
| cabin_2023 | 200 | 7 | 349 | 39772 | 2856.615 |

Numeric serving bounds are deliberately not applied in this diagnostic; cabin
validation itself is outside the training lead window. These scores cannot
validate a replacement serving rule. Network threshold five admits 50 airports
but only 420 validation rows from one collection day; threshold ten has only
11. Different threshold rows select different subsets, so a lower MAE is not an
apples-to-apples improvement. Currency/target gaps remain regardless of counts.
No evidence justifies lowering the current rule or promoting a rejected airport.

Better future rules need independent query-day/flight-date clusters, route/class
error and interval calibration within the accepted numeric domain, and an
untouched time period. They should measure distinct itinerary support rather
than treating every correlated row as an independent sample.

## Exact per-airport summary

Network maximum is the largest fitting profile touching that endpoint; cabin
cells count eligible profiles touching it. Each row's full explanation and
temporal/semantic measures are in the CSV.

| iata_code | origin_observations | destination_observations | directional_routes | network_2020_largest_profile | cabin_2023_eligible_profiles | research_eligible |
| --- | --- | --- | --- | --- | --- | --- |
| AGR | 17 | 0 | 3 | 0 | 0 | False |
| AGX | 22 | 0 | 2 | 1 | 0 | False |
| AJL | 236 | 0 | 8 | 5 | 0 | False |
| AMD | 47339 | 43050 | 56 | 13 | 138 | True |
| ATQ | 1007 | 0 | 18 | 9 | 0 | False |
| BBI | 1324 | 81 | 23 | 12 | 0 | False |
| BDQ | 646 | 86 | 18 | 10 | 0 | False |
| BHJ | 21 | 0 | 2 | 3 | 0 | False |
| BHO | 729 | 57 | 19 | 12 | 0 | False |
| BHU | 4 | 16 | 3 | 3 | 0 | False |
| BLR | 76995 | 72229 | 66 | 14 | 170 | True |
| BOM | 84789 | 82339 | 70 | 17 | 209 | True |
| CCJ | 419 | 93 | 15 | 9 | 0 | False |
| CCU | 56922 | 54349 | 57 | 11 | 153 | True |
| CDP | 6 | 0 | 2 | 1 | 0 | False |
| CJB | 892 | 510 | 23 | 11 | 0 | False |
| CNN | 64 | 62 | 10 | 6 | 0 | False |
| COK | 1667 | 895 | 37 | 17 | 0 | False |
| DED | 682 | 329 | 28 | 9 | 0 | False |
| DEL | 85230 | 78212 | 76 | 14 | 216 | True |
| DHM | 12 | 3 | 2 | 2 | 0 | False |
| DIB | 40 | 103 | 9 | 7 | 0 | False |
| DIU | 0 | 6 | 1 | 2 | 0 | False |
| DMU | 12 | 47 | 4 | 4 | 0 | False |
| GAU | 1099 | 846 | 33 | 14 | 0 | False |
| GAY | 18 | 26 | 4 | 3 | 0 | False |
| GOI | 1373 | 1109 | 34 | 10 | 0 | False |
| GOP | 48 | 130 | 9 | 4 | 0 | False |
| GWL | 0 | 31 | 1 | 4 | 0 | False |
| HBX | 137 | 178 | 11 | 8 | 0 | False |
| HJR | 1 | 10 | 2 | 0 | 0 | False |
| HYD | 58468 | 63629 | 65 | 14 | 148 | True |
| IDR | 628 | 755 | 28 | 8 | 0 | False |
| IMF | 162 | 317 | 15 | 8 | 0 | False |
| ISK | 0 | 3 | 2 | 1 | 0 | False |
| IXA | 208 | 506 | 17 | 14 | 0 | False |
| IXB | 197 | 604 | 14 | 8 | 0 | False |
| IXC | 540 | 909 | 23 | 10 | 0 | False |
| IXD | 46 | 86 | 10 | 3 | 0 | False |
| IXE | 290 | 580 | 21 | 10 | 0 | False |
| IXG | 34 | 72 | 7 | 3 | 0 | False |
| IXI | 2 | 14 | 3 | 2 | 0 | False |
| IXJ | 350 | 656 | 19 | 9 | 0 | False |
| IXL | 20 | 213 | 8 | 7 | 0 | False |
| IXM | 149 | 597 | 16 | 13 | 0 | False |
| IXP | 0 | 2 | 1 | 1 | 0 | False |
| IXR | 186 | 638 | 14 | 9 | 0 | False |
| IXS | 16 | 126 | 8 | 6 | 0 | False |
| IXU | 41 | 158 | 6 | 7 | 0 | False |
| IXZ | 147 | 489 | 18 | 9 | 0 | False |
| JAI | 649 | 1293 | 37 | 11 | 0 | False |
| JDH | 101 | 359 | 12 | 7 | 0 | False |
| JGA | 0 | 25 | 2 | 1 | 0 | False |
| JLR | 1 | 220 | 10 | 4 | 0 | False |
| JRG | 0 | 16 | 3 | 1 | 0 | False |
| JRH | 3 | 18 | 7 | 2 | 0 | False |
| JSA | 4 | 19 | 6 | 3 | 0 | False |
| KLH | 0 | 13 | 2 | 1 | 0 | False |
| KNU | 0 | 33 | 4 | 3 | 0 | False |
| KQH | 0 | 4 | 2 | 0 | 0 | False |
| KUU | 0 | 23 | 2 | 2 | 0 | False |
| LKO | 579 | 1330 | 30 | 13 | 0 | False |
| MAA | 56861 | 59764 | 53 | 13 | 150 | True |
| MYQ | 0 | 13 | 2 | 4 | 0 | False |
| NAG | 108 | 934 | 24 | 10 | 0 | False |
| NDC | 0 | 49 | 5 | 3 | 0 | False |
| PAT | 370 | 1581 | 27 | 11 | 0 | False |
| PBD | 0 | 9 | 2 | 1 | 0 | False |
| PGH | 0 | 9 | 2 | 1 | 0 | False |
| PNQ | 261 | 2143 | 34 | 11 | 0 | False |
| PNY | 6 | 5 | 3 | 0 | 0 | False |
| RAJ | 30 | 289 | 7 | 11 | 0 | False |
| RDP | 0 | 80 | 3 | 6 | 0 | False |
| RJA | 7 | 69 | 6 | 11 | 0 | False |
| RPR | 172 | 1289 | 25 | 9 | 0 | False |
| SAG | 0 | 207 | 9 | 3 | 0 | False |
| SLV | 0 | 2 | 1 | 0 | 0 | False |
| STV | 60 | 685 | 24 | 8 | 0 | False |
| SXR | 67 | 1246 | 25 | 8 | 0 | False |
| TCR | 0 | 15 | 2 | 1 | 0 | False |
| TEZ | 0 | 11 | 4 | 1 | 0 | False |
| TIR | 77 | 399 | 15 | 7 | 0 | False |
| TRV | 112 | 1074 | 22 | 9 | 0 | False |
| TRZ | 0 | 192 | 6 | 6 | 0 | False |
| UDR | 77 | 856 | 17 | 9 | 0 | False |
| VGA | 54 | 538 | 14 | 11 | 0 | False |
| VNS | 0 | 1497 | 25 | 10 | 0 | False |
| VTZ | 0 | 1374 | 25 | 11 | 0 | False |
