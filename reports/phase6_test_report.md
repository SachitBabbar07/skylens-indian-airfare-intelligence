# Final test report — 16 November 2026

| Acceptance check | Executed result |
| --- | --- |
| Installation and startup | `setup.ps1` sync and `npm ci`/build passed with Vite stopped; unchanged `run.ps1` started and logged 2 loaded models, 0 unavailable; health 200 |
| Full Python | 160 passed in a clean full environment; two upstream TestClient deprecation warnings |
| Source-only dependencies | 101 portable tests passed in a separate minimal environment |
| Frontend | 15 tests passed, TypeScript/Vite production build passed |
| Native HTTP matrix | 592 exact profiles, 1,776 predictions, 592 matching additive explanations, 15 expected 422 rejections, zero unexpected failures |
| Product boundary | Customer and legacy paths 503; null currency; no served interval; unknown/nonfinite research input safely rejected |
| Intake | Actual empty CSV validation and summary returned zero records; software tests exercise documented grants, missing/changed evidence, conflicts, retention and split isolation |
| Integrity | All 56 original model/data artifacts and five protected training/launch files match SHA-256; three Phase 5 audit archives and seven extracted files match |
| Security and config | Zero findings in repository guards; `pip-audit` and `npm audit` found no known vulnerabilities after upgrading affected pins; explicit CORS allowed local preflight and rejected unrelated origin. Dependency compatibility and Git object checks passed |

An initial setup run while Vite was active encountered Windows’ `esbuild.exe` file lock. Setup passed after stopping Vite, without elevated permissions. Installation instructions now call that out. A clean full environment also resolved all 47 pins and ran the complete native suite.

Python audit updates: Starlette 0.46.2 → 1.3.1 with FastAPI 0.138.0, PyArrow 21.0.0 → 23.0.1, pytest 8.4.1 → 9.0.3. Vite 6.4.6 already includes the [maintainer’s patch](https://github.com/vitejs/vite/security/advisories/GHSA-p4f5-76q4-ffq7). Audit and publication scans are scoped checks, not an exhaustive penetration test.

Warm Windows loopback measurements, 20 requests per endpoint: median 1.16 ms health, 15.11 ms route evidence, 6.94 ms inference and 39.83 ms SHAP. Route metadata transferred 10,600 gzip bytes from 171,106 uncompressed bytes. Production bundles were about 69 KB JS and 4 KB CSS compressed. This is a local demonstration measurement, not a load-test claim.

[HTTP matrix receipt](phase6_http_matrix.json) · [Integrity and timings receipt](phase6_verification.json) · [Browser acceptance](phase6_browser_qa.md)
