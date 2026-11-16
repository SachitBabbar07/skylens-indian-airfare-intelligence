# Final system status — 16 November 2026

**Ready for demonstration as a local research application. Customer fare prediction remains disabled.** Both saved CatBoost models load using `D:\SkyLens\run.ps1`. Only the cabin model has eligible research profiles. Native model outputs and SHAP are explicitly unverified numerical units; no current price, INR estimate or live booking quote is displayed.

| Component | Verified release behavior |
| --- | --- |
| Overview | Customer status and prerequisites, real coverage counts and empty quote intake assets |
| Coverage | 661 directory records; 88 historical endpoints and 720 directional routes; separate dataset/cabin counts and eligible profile filters |
| Research tools | 7 airports, 42 routes and 592 exact profiles; acknowledged inference, 13 SHAP contributions, withheld intervals |
| Saved evaluation | Both frozen models’ final-test metrics and cohort date ranges |
| Intake | Empty CSV and machine-readable schema, offline validation/ingestion with permission and evidence checks |
| Operations | Loopback health/model diagnostics, gzip metadata, safe request errors, retry after real backend restart |

[Verified installation and launch](../docs/INSTALLATION.md) · [Acceptance tests](phase6_test_report.md) · [Browser report](phase6_browser_qa.md) · [Limitations](phase6_data_model_limits.md) · [GitHub delivery](github_delivery_report.md)
