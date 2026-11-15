# Dataset guide

## Phase 3 quote intake and Git distribution

No genuine new quote has been acquired. [Source access](../reports/quote_source_access_audit.md) distinguishes live offers, sandbox data, cached indicative prices, tracking, surveys and historical files. The [quote collection guide](QUOTE_COLLECTION_GUIDE.md) provides an empty CSV and permission/evidence workflow. Unknown currency, taxes, fees, passenger basis or journey meaning cannot enter the new all-in single-adult INR target. One-way and actual return quotes remain separate. The quote store is private and never read by the existing training code.

Git distributes original code, research findings, schema/hash/license metadata, aggregate metrics/coverage and configuration. Original archives, raw/processed/interim data, native model binaries, individual prediction/exclusion outputs, example explanations, full third-party source cards/README/code snapshots, local checkpoints, screenshots and quote evidence remain local. The MIT code license does not relicense data or grant acquisition/ML rights. See [reconstruction](INSTALLATION.md#source-only-research-reconstruction) and the licensing report for source attribution and restrictions. Detailed original file profiles/source cards are local audit artifacts; reacquire them only where permitted.

## Historical sources
Use reports/dataset_discovery_report.md and dataset_comparison.csv for every assessed candidate, source URL, license declaration and rejection reason. Actual schemas, hashes, row counts and missing values are in data/metadata/file_profiles.json; immutable raw archives are retained locally.

Yash Dharme's 2023 raw source provides seven cities, three sufficiently represented cabin classes and a booking date, but all queries belong to one collection day. PromptCloud provides broader geography across three collection days, without cabin and standardized price definitions. These are separate research cohorts, never a pooled INR target.

The 2022 EaseMyTrip file is a reference. The Goibibo candidate has matching ordered flight IDs, dates shifted 500 days and altered prices, so it is not independent validation. The broad 2019–2025 candidate lacks authentic collection evidence and has questionable route/time fields. Its authenticity is unverified, rather than asserted to be proven synthetic. MakeMyTrip's 404 rows explicitly exclude taxes and lack key quote settings, so they cannot validate a total-price model.

Airport masters and schedules do not contain ticket prices; traffic files do not become fare observations; aggregate fare indexes are not individual quotes. ATL international returns do not establish domestic return support. The HF schedule original has unknown rights, and a mirror's MIT tag does not cure that. Publisher licenses and upstream-rights caveats appear in dataset_licensing_and_provenance.md. No paid API, credentials or unauthorized scraping is required.
