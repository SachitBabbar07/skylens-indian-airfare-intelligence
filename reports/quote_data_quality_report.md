# Quote data quality

Computed from the actual private quote store, not unit-test fixtures.

| measure | value |
| --- | --- |
| raw_rows | 0 |
| malformed_rows | 0 |
| duplicate_snapshots | 0 |
| conflicted_rows_excluded | 0 |
| retained_unique_snapshots | 0 |
| verified_targets | 0 |
| research_only_or_unusable | 0 |
| unique_itineraries | 0 |
| collection_days_ist | 0 |
| itinerary_days | 0 |
| genuine_round_trip_targets | 0 |
| training_automatically_enabled | False |

No source passed the access/retention/reuse gate during Phase 3. No quote CSV was ingested, so currency-verified totals, known taxes, known passenger basis and genuine return targets each number **zero**. Missingness percentages, acceptance rates and duplication rates are undefined with no actual input; zero rows is not a 100% quality score. The header-only template is not evidence. Synthetic software fixtures live only in temporary test directories and never enter this store or training.

The importer preserves authorized raw bytes, source permission snapshots and evidence hashes; checks schema/time/price/product consistency; separates research-only and quarantined rows; rejects unapproved access before retaining payload; preserves repeat snapshots and excludes conflicts. Tests exercise these behaviors using explicitly synthetic fixtures. A passing software test does not demonstrate source authenticity or a model-quality improvement. See [manual instructions](../docs/QUOTE_COLLECTION_GUIDE.md).
