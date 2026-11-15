# Frontend guide
React + TypeScript + Vite, ordinary CSS and system fonts keep the UI small and free of external runtime services. main.tsx owns metadata loading, scenario state, API calls, airport comboboxes, the directory and model tables. style.css supplies a warm-neutral/navy editorial design with responsive layout rules.

Every airport/carrier/class/profile choice comes from the API. Endpoint changes choose an eligible route; cabin/carrier/stops depend on joint support, not independent hard-coded lists. Defaults use observed field minima for a hypothetical historical scenario, not an advertised real flight schedule. Numeric fields show support ranges. A model without eligible cells displays the reason and remains inspectable in coverage and methodology.

Submission clears old output, calls /predict and /explain, and displays output only when both succeed. API failure never becomes a sample fare. Loading, no-result and error states are explicit. Airport search supports names, cities and codes plus arrow keys, Enter and Escape. Labels, focus rings, live regions and reduced-motion rules are included. Tables scroll in their own containers on small screens.

The TypeScript production build passes. Browser permission was declined, so actual keyboard interaction, responsive overflow and visual appearance remain unverified browser QA items.
<!-- SKYLENS_PHASE2_START -->
## Phase-two update

See PHASE2_FINDINGS.md for the current audit. Currency and full fare scope remain
unknown. The API now withholds intervals because the historical final holdout
does not overlap its serving ranges; it exposes /fare-semantics and explicit
airport serving statuses. Seven clock-rounding rejection cases were fixed with
microsecond-scale normalization. Tests and HTTP checks pass; browser QA remains
blocked by the saved permission policy. Existing models and training data were
preserved, and no wider serving or full retraining was justified.
<!-- SKYLENS_PHASE2_END -->
