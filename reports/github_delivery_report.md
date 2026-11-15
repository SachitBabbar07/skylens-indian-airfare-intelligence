# GitHub delivery status

Local version control is initialized at `D:\SkyLens` on `main`. GitHub CLI v2.104.0 was obtained from its official release and checked against published SHA-256. The existing Git Credential Manager authorization successfully identifies the personal account **SachitBabbar07** (user ID 244026342). Credentials are passed only in a CLI child-process environment, never written to this project or displayed. The CLI warns about absent `read:org`; no organization access is needed or requested. Personal repository operations have succeeded with the existing `repo`/`workflow` scopes. The integration is installed but exposes no repository tools to this running chat.

Repository created and independently read back: [SachitBabbar07/skylens-indian-airfare-intelligence](https://github.com/SachitBabbar07/skylens-indian-airfare-intelligence), owner **SachitBabbar07**, visibility **PRIVATE**. Both REST and GraphQL name checks found no existing repository before creation. First push/default branch/remote contents are being verified; no completion tag has been created.

## Prepared project and exclusions

The selected name was available; no alternative name or existing-repository overwrite was needed. Intended default branch: `main`. No organization destination, public visibility, force push, paid service or Git LFS is used.

Source folders `backend`, `frontend` (source/lockfiles), `src`, `scripts`, `tests`, `config`, `docs`, normalized `data/metadata`, model metadata/support/importance and research `reports` are prepared for upload. MIT applies to original code/docs only. Raw/processed/interim datasets, native model binaries, prediction-row outputs, source examples/full third-party snapshots, quote evidence, backups, dependencies, build output and local tools are excluded. [Installation](../docs/INSTALLATION.md) explains lawful acquisition, explicit reconstruction and exact artifact restoration.

The first local pre-upload snapshot is preserved on `archive/local-phase2-baseline` and in the Phase 3 checkpoint. Before any upload, individual examples embedded in its registry were removed from the publishable baseline. Its original local history remains preserved; the archive branch is **local only and must not be pushed**. No remote history exists or was rewritten. Use `git push origin main`, never `--all`, to avoid publishing local audit history.

The repository guard scans staged files and all blobs in the intended current branch ancestry for known credential patterns, private paths, row samples and files above 5 MiB. It does not prove absence of every secret or legal risk, so human diff/license review remains required. Final exact scan/blob/test/commit results will be recorded after the last commit.

## Zero-cost CI gate

Private GitHub-hosted compute can incur charges beyond included usage. The billing lookup returned 404 and required an additional `user` scope; no broader access was requested. To honor INR 0, both jobs are gated by repository variable `SKYLENS_CI_ZERO_SPEND_CONFIRMED=true`, initially unset. Confirm free included compute and a zero-overage stop/no-payment safeguard before enabling. A skipped run is not a passed check. Local portable/native tests and builds do not depend on hosted CI. [Official billing rules](https://docs.github.com/en/actions/concepts/billing-and-usage).

## Clone, pull and run

```powershell
git clone https://github.com/SachitBabbar07/skylens-indian-airfare-intelligence.git
cd skylens-indian-airfare-intelligence
git config core.hooksPath .githooks
git pull --ff-only
```

Use Git's secure credential-manager sign-in for private access, or complete standard GitHub CLI web sign-in; never paste tokens into chat. Follow [installation](../docs/INSTALLATION.md) and [contributing](../CONTRIBUTING.md). A clone does not include private datasets/native models or historical machine-local checkpoints.
