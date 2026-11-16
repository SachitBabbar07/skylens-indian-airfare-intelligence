# Flight search verification

**16 November 2026** · Windows · `feature/flight-search`

| Check | Observed result |
| --- | --- |
| Startup and build | `run.ps1` started FastAPI with both frozen research models loaded. TypeScript and Vite built both pages. |
| Automated checks | 192 Python tests, 133 Python tests in the portable environment, and 19 frontend tests passed. Python reported two existing TestClient deprecation warnings. |
| Airport directory | The API returned 165 IATA-coded Indian airports. Browser search found PNQ by city, DEL by code and AYJ by airport name. The same airport was excluded from the opposite field. Swapping updated both endpoints. |
| Journey and travellers | Both valid journey types submitted through the built app. The Return field follows Round Trip and blocks dates earlier than departure. Adult counts updated on desktop and mobile. Economy was the only cabin displayed with no registered provider. |
| Fare request and reliability | Both journeys returned the expected 503 `unconfigured` with no fare displayed. Stopping FastAPI made the Vite app disable Search Flights and offer Retry connection. Restarting FastAPI and retrying restored autocomplete. No application console errors or warnings were captured during browser checks. |
| Responsive browser | Checked 360, 390, 768, 1024 and 1440 px. Document width stayed within the available viewport. The form stacked on phones and used a single row at 1024 and 1440 px. |
| Research regression | Research opened from Flights and linked back. The acknowledged cabin profile returned the raw output and SHAP explanation in unverified model-output units. The saved final-test evaluation table rendered. |
| Fare contract | Isolated tests exercised multiple quotes, INR and other currencies, unavailable routes, empty results, auth/quota/rate-limit/timeout failures, malformed and stale fare responses, and validated-model routing. These tests use software fixtures. |

Live provider authentication, real itinerary results, provider-specific traveller and cabin options, and account quota remain unverified. Both live fare and customer ML capabilities are disabled. The released `v0.1.0` tag refers to Research Edition.

## Cleanup

Removed untracked, ignored `.tools/phase6_ui.py` and `.tools/phase6_tidy.py` after checking Git history, references, tests and runtime use. These one-time scripts patched the prior Research entry point in place. Their changes are already in the release. Hash-verified copies are stored locally under `backups/flight-search-cleanup/`. The original datasets, model files, historical reports and provenance remain in place.
