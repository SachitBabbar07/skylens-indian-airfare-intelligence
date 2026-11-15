# Phase 5 price-definition audit

The original three publisher cards were fetched again: HTTP 200, version 1, declared CC0. Their descriptions, original headers and preserved preparation code still do not establish currency, all mandatory taxes/fees, total/base scope, passenger basis or genuine booking type. [Fresh receipts](../data/metadata/phase5/original_source_reaudit.json). Single-direction rows remain unverified booking types.

- **APIx export:** INR is a publisher/collector label; the collector contains a hard-coded INR assignment. All 26,018 raw rows and 142 cleaned rows have no full breakdown; base, tax, airport-fee and convenience components are missing. One-adult query parameters do not independently establish complete per-record target semantics. No dataset license was found.
- **HybridAni:** all 1,872 historical rows satisfy the supplied component arithmetic. This does not prove mandatory inclusions, currency, passenger basis or booking type. Those definitions, timezone and data reuse grant remain undocumented.
- **Kaggle mirrors:** matching legacy fields do not supply missing source definitions. The Usman notebook explicitly replaces the target with capped prices; those are not untouched new observations.
- **Official tariff:** [Air India](https://rde.airindia.com/content/dam/air-india/pdfs/TARIFF-SHEET-AS-ON-01-NOV-24.pdf) documents rupee base fares plus additional charges, not selectable dated totals. No calculated tariff total was fabricated as a quote.

Unknown definitions remain unknown; no FX, passenger division, fee imputation or currency relabelling. [Author clarification draft](phase5_author_clarification_draft.md) is prepared and **not sent**.
