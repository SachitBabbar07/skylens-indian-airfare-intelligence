# Prediction target decision (before diagnostic fitting)

The existing target remains the source-recorded numeric fare, isolated by collector.
No selected source's currency, tax/fee scope, passenger count or booking journey type
was established from its original card, public file metadata or raw records. No FX
conversion or INR relabeling is justified. Newly inspected files do not provide a
compatible authentic total-fare target. Existing data and models will be retained.

A future product target should be a documented INR total per adult passenger for
one specified one-way itinerary and cabin, with known taxes/fees, query timestamp,
departure date and source reuse rights. Genuine return targets require an actual
whole-return quote and return date. Base fares/aggregates require separate targets.

Full production retraining is not justified. Additional fitting, if performed in
this phase, is development-only support sensitivity and two-airport generalization,
using the unchanged research target. It cannot change the frozen serving artifact
or use the final test to select a new rule. A fresh independent evaluation and
documented fare semantics are required before promotion.

The cabin artifact fits lead days 1–35, calibrates on 36–40, and tests on 41–50.
Zero of its final-test rows passes the current serving ranges. Therefore the old
aggregate interval coverage is offline evidence, not validation for a served
scenario. Intervals will be withheld from responses; point research estimates and
historical offline metrics remain available.
