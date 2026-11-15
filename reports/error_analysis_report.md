# Error analysis
Worst final-test routes with >=30 observations:

| cohort | group | n | mae | rmse | p90_absolute_error |
| --- | --- | --- | --- | --- | --- |
| network_2020 | DEL-GOI | 33 | 3602.29 | 5490.77 | 10265.93 |
| network_2020 | BOM-COK | 48 | 2247.26 | 3366.22 | 5524.47 |
| network_2020 | COK-HYD | 30 | 2157.96 | 4234.14 | 3324.28 |
| network_2020 | BLR-CCU | 45 | 1928.48 | 3142.14 | 3368.76 |
| network_2020 | CCU-DEL | 31 | 1734.2 | 2520.12 | 4393.4 |
| network_2020 | BOM-HYD | 30 | 1652.57 | 2666.65 | 3270.14 |
| network_2020 | BOM-CCU | 32 | 1589.28 | 2151.8 | 3997.21 |
| network_2020 | BLR-BOM | 33 | 1393.19 | 2061.36 | 3007.85 |
| cabin_2023 | AMD-MAA | 1471 | 4429.79 | 7061.07 | 9975.53 |
| cabin_2023 | AMD-CCU | 1095 | 4081.56 | 6373.76 | 7939.13 |
| cabin_2023 | AMD-BOM | 1715 | 3956.9 | 6291.53 | 8987.1 |
| cabin_2023 | AMD-HYD | 1600 | 3673.93 | 5711.5 | 9091.79 |
| cabin_2023 | MAA-AMD | 1583 | 3597.2 | 6030.0 | 9170.13 |
| cabin_2023 | AMD-BLR | 1525 | 3465.6 | 5368.8 | 9427.63 |
| cabin_2023 | BLR-AMD | 1298 | 3328.32 | 5509.2 | 10526.77 |
| cabin_2023 | CCU-AMD | 606 | 3299.11 | 5529.83 | 6902.11 |

Development-only stress tests (individual results, not an inflated pooled score):

| cohort | protocol | n | mae | rmse |
| --- | --- | --- | --- | --- |
| network_2020 | random_quote_group_holdout | 1406 | 2375.57 | 4163.64 |
| network_2020 | route_holdout_known_airports | 2493 | 2428.66 | 4219.53 |
| network_2020 | route_holdout_known_airports | 2226 | 2482.23 | 4305.0 |
| network_2020 | route_holdout_known_airports | 2276 | 2424.17 | 4026.07 |
| network_2020 | unseen_airport_holdout | 1022 | 2350.39 | 3679.84 |
| network_2020 | unseen_airport_holdout | 82 | 3584.72 | 6242.14 |
| cabin_2023 | random_quote_group_holdout | 62419 | 3489.79 | 6220.19 |
| cabin_2023 | route_holdout_known_airports | 113302 | 4489.17 | 7281.68 |
| cabin_2023 | route_holdout_known_airports | 101399 | 4404.15 | 7087.93 |
| cabin_2023 | route_holdout_known_airports | 97267 | 4385.05 | 7206.56 |
| cabin_2023 | unseen_airport_holdout | 113186 | 4996.45 | 8437.13 |
| cabin_2023 | unseen_airport_holdout | 112290 | 4415.51 | 6920.51 |
| cabin_2023 | unseen_airport_holdout | 101082 | 4603.37 | 7320.11 |
| cabin_2023 | unseen_airport_holdout | 82632 | 4262.47 | 6899.64 |
| cabin_2023 | unseen_airport_holdout | 78145 | 4125.74 | 6649.17 |
| cabin_2023 | unseen_airport_holdout | 75984 | 5503.77 | 8763.15 |
| cabin_2023 | unseen_airport_holdout | 60617 | 5675.68 | 8572.04 |

Sparse-cell errors are unstable rankings. Expensive but valid fares remain and can dominate RMSE. Subgroup tables expose weaknesses that overall R² hides. The wider network fails serving support despite 88 observed airports. Stronger familiar-city results cannot establish nationwide reliability. Geographic holdouts and route holdouts answer different questions.
