# Data pipeline guide
A canonical schema means translating available information into consistent column names without pretending missing information exists. For example, 02h 05m becomes duration_minutes=125. An unknown network cabin stays Unspecified. Unknown currency and fare scope remain null/unknown, and normalized_price_inr remains missing.

Explicit city aliases join to actual nonempty IATA keys. Unresolved or international endpoints and layovers are excluded, with a reason. Empty layover slots legitimately mean no additional recorded stop. Historical Goa maps to GOI, and old Rajkot fares stay RAJ instead of being transferred to HSR. Coordinates yield approximate great-circle distance, not flown itinerary length.

Exact canonical duplicates are removed before splitting; valid expensive fares remain. Quote keys group the same itinerary independently of its price. Earlier appearances in a later partition are purged. Fingerprints and quote groups are checked across all split pairs. No full-data target statistics are used; fitted encoders/scalers are inside training pipelines.

Data leakage means giving the learner information it would not have when making a new prediction. Keeping prices, quote IDs and future outcomes out of features avoids direct leakage. Keeping the final test separate avoids evaluation leakage. Reports and split manifests show the actual checks. A single query snapshot still confounds booking lead time and departure date; more feature columns cannot repair missing collection history.
