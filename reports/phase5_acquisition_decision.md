# Phase 5 acquisition decision

**Do not incorporate candidate files or retrain.** No inspected source passes the full target/provenance/reuse checks. Customer fare prediction and served intervals remain disabled; research tools stay operational.

The three publicly offered Kaggle archives are frozen in [an audit-only manifest](../config/phase5_sources.json). `python -m skylens.source_audit` verifies local archives/files; `--download` explicitly permits pinned public downloads. Checksums, exact membership, path safety and expansion limits are enforced. Denials/rate limits are terminal. `python scripts/phase5_quality.py` reproduces their quality/lineage comparison against the locally restored original source. These commands do not train or alter canonical data.

GitHub CSVs with unresolved data rights remain local inspection evidence, outside automated training/acquisition. APIx's author acknowledges that missing robots.txt is not permission; the ixigo collector documents a restriction-bypass flag, which was never used. [Current ixigo terms](https://www.ixigo.com/about/terms-of-use/) restrict automated access and systematic database collection; [Air India terms](https://www.airindia.com/in/en/terms-and-condition.html) restrict automated/manual copying without permission. No carrier/OTA booking endpoint was queried.

The empty CSV/schema, optional source-license/reuse assertions and checked lead time are available for authorized manual intake. Assertions never override source grants, semantic evidence, retention rules or conflict review. No new source grant, payment, account, paid dependency or external message was created.
