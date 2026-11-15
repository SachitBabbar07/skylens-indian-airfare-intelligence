# Installation and reconstruction

SkyLens is a local Windows-first research application. Use Python 3.12, Node 22 or newer, Git, and free [uv](https://docs.astral.sh/uv/). The pinned Python dependencies are in `requirements.txt`; frontend dependencies use `frontend/package-lock.json`. No API key, paid account or live airfare service is needed for the existing application.

## Existing research workspace

```powershell
Set-Location D:\SkyLens
.\setup.ps1
.\.venv\Scripts\python.exe -m pytest -q
.\run.ps1
```

Open `http://127.0.0.1:8000` and `/docs`. `run.ps1` loads existing native model artifacts; it never retrains. Stop with Ctrl+C. If this machine's PowerShell execution policy blocks a script, follow the organization's approved policy; do not bypass it automatically. Build assets with `npm --prefix frontend ci` then `npm --prefix frontend run build`. The frontend dev server uses `npm --prefix frontend run dev` alongside the API. CORS is documented in `.env.example`; variables come from the process environment, not an automatic dotenv loader.

## Portable checks

The owner has made the source repository public. The existing hosted-CI gate
remains disabled under the owner's earlier instruction; publication does not
automatically enable it. Public cloning needs no GitHub login.

A source-only clone intentionally contains no raw/processed data, native model binary, private quote evidence or local audit backup. Install just the portable test dependencies when model work is unnecessary:

```powershell
uv venv --python 3.12 .venv
uv pip install --python .venv/Scripts/python.exe -r requirements-ci.txt
.\.venv\Scripts\python.exe -m pytest tests/test_quotes.py tests/test_portable_contract.py -q
.\.venv\Scripts\python.exe -m compileall -q src backend scripts
npm --prefix frontend ci
npm --prefix frontend run build
```

On Linux/macOS use `.venv/bin/python` and `PYTHONPATH=src`. GitHub Actions is configured for the portable tests/compile/scanner checks and real frontend build without dataset downloads or API keys. It does not claim native-model validation. Actions uses commit-pinned actions, read-only repository permissions and bounded runtimes. In a private repository, hosted compute can incur overage charges. Jobs remain skipped until the owner confirms included compute availability and a zero-overage stop/no-payment safeguard, then sets repository variable `SKYLENS_CI_ZERO_SPEND_CONFIRMED=true`. No spending or billing change is performed by setup. Skipped jobs are not a passed CI verification. Revoke the variable if the zero-spend assurance changes. [GitHub billing](https://docs.github.com/en/actions/concepts/billing-and-usage).

The original tests in `test_skylens.py` and `test_phase2_reliability.py` are intact and marked `local_data`. Default `pytest -q` still runs them and fails if required local artifacts are absent. Marker deselection alone does not prevent module imports, so lightweight CI explicitly selects portable test files. The full 48-test historical regression baseline also needs the original `backups/phase2_*/baseline_manifest.json` for checkpoint comparisons. That machine-local historical checkpoint cannot be recreated honestly by merely fitting new models.

## Source-only research reconstruction

1. Read [dataset guide](DATASET_GUIDE.md), [license audit](../reports/dataset_licensing_and_provenance.md), [selection](../reports/dataset_selection_decision.md) and [Phase 2 findings](PHASE2_FINDINGS.md). Confirm current source access/licenses and your intended rights **before** downloads. Publisher-declared open licenses do not resolve all upstream rights. No dataset or model redistribution is promised by this repository.
2. `config/sources.json` pins original public versions, archive hashes and the OurAirports commit/file hashes. `data/metadata/dataset_registry.json` records URLs, schemas, licenses and decisions. `scripts/acquire.py` replays all eight original audit archives and checks hashes; `scripts/phase2_acquire_candidates.py` replays the four audit-only distributions. They are optional research procedures, **not** part of setup/CI. Do not run a source whose current terms do not permit your use. Do not bypass a 403, login requirement, changed file or checksum mismatch; obtain lawful access or stop and record the limitation.
3. For manual authorized acquisition, place the unchanged archives/extracted filenames at the registry's `data/raw/...` paths and confirm pinned hashes. OurAirports files use the pinned Git commit. Source schemas/versions must match; do not replace them silently with a newer similarly named file.
4. To reconstruct fresh **research** artifacts after lawful acquisition, use the full pinned requirements via `setup.ps1`, set `$env:PYTHONPATH='src'`, run `python -m skylens.prepare`, then run training in a separate experiment checkout with `python -m skylens.train` and `python -m skylens.report`. These commands overwrite generated local cohort/model/report files, so preserve current artifacts/checkpoints first. Training is explicit and takes CPU/time; do not run it merely to install, import quotes or launch the existing workspace. Exact binary reproducibility across platforms/package versions is not guaranteed; regenerated metadata must bind the actual artifact hash. Historical model hashes are evidence, not a promise that a fresh fit has identical bytes.
5. Restoring the exact original artifacts is different from fitting a reconstruction. Use the user's authorized local archive/backups and verify the hashes in model metadata. They are deliberately absent from GitHub. Retain source rights, not just a binary file.
6. With full local artifacts, run `pytest -q`, start `run.ps1` in one terminal, then `python scripts/smoke.py --output reports/local_http.json` and `python scripts/phase2_http_qa.py --output reports/local_http_matrix.json` in another. Browser QA requires the separate saved localhost permission to be enabled normally by the user/administrator.

## Quote intake only

Follow [QUOTE_COLLECTION_GUIDE.md](QUOTE_COLLECTION_GUIDE.md). The importer works offline with portable dependencies and the included reviewed airport directory. The template has no example fare; the permission file authorizes no source. The importer cannot turn an unlicensed source, an API sandbox, unknown scope or historical source units into a verified INR target. It never retrains or changes the API.
