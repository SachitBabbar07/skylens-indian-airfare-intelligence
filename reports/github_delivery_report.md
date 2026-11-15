# GitHub delivery status

**Browser QA follow-up, 15 November 2026:** permissions now allow both localhost
origins. Desktop/mobile flows passed after fixing documentation proxying and
blank-number warnings. Tests remain 102 passing; model/data hashes are unchanged.
See [browser findings and screenshots](browser_qa_followup_20261115.md). The original
source receipt below remains pinned to its Phase 3 implementation revision;
the browser follow-up is a subsequent verified milestone on the same private main.

Local version control is initialized at `D:\SkyLens` on `main`. GitHub CLI v2.104.0 was obtained from its official release and checked against published SHA-256. The existing Git Credential Manager authorization successfully identifies the personal account **SachitBabbar07** (user ID 244026342). Credentials are passed only in a CLI child-process environment, never written to this project or displayed. The CLI warns about absent `read:org`; no organization access is needed or requested. Personal repository operations have succeeded with the existing `repo`/`workflow` scopes. The integration is installed but exposes no repository tools to this running chat.

Repository created, pushed and independently read back: [SachitBabbar07/skylens-indian-airfare-intelligence](https://github.com/SachitBabbar07/skylens-indian-airfare-intelligence), owner **SachitBabbar07**, visibility **PRIVATE**, default branch **main**. REST and GraphQL checks found no existing repository before creation. Normal fast-forward milestone pushes succeeded; no completion tag or force push was used.

## Version-control verification

| Item | Verified result |
| --- | --- |
| Workspace | `D:\SkyLens`; repository initialized only here |
| Remote | `origin=https://github.com/SachitBabbar07/skylens-indian-airfare-intelligence.git` for fetch/push |
| Published branch | `main`, tracking `origin/main`; no other remote branch |
| Local branches | `main`, `archive/local-phase2-baseline` (never uploaded) |
| History | Initial Phase 3 delivery: six published commits. The browser follow-up adds a subsequent verified milestone; inspect the live main tip for current history. One original pre-upload snapshot remains local. |
| Validated implementation revision | `30e1a2efca23770221f5550607c678663618cc3f` — Vite security patch; the following audit-record commit contains this report. See `git log -1` or the live main branch for the final delivery tip, also supplied in chat. |
| Remote integrity | `git ls-remote` and GitHub REST commit SHA matched the local implementation revision; default branch/owner/private visibility read back independently |
| README/docs | Remote README HTML and source-document blob hashes were verified at initial delivery. Local Markdown links are checked after updates. Desktop/mobile browser QA has since passed the linked follow-up. |
| Data/artifact exclusion | Remote tree contains no raw/processed/quote payloads, native model binaries, backup archives or local tools. 159 files at the validated source revision; final audit files follow. |
| Secret/size review | Staged and full current-branch ancestry scans: zero findings. Largest uploaded blob 255,191 bytes; no blob exceeds 5 MiB. Pre-push hook executed on milestone pushes. This focused scanner is supplemented by diff/license/privacy review. |
| Local tests | 102 passed: original 48 plus 54 portable software checks; no failure/error/skip, one upstream deprecation warning |
| Clean remote clone | Git clone/pull succeeded; 54 portable tests passed without CatBoost/pandas or native/data artifacts. TypeScript/Vite build, compile, docs links and ancestry guard passed. |
| Dependency correction | Clean installation exposed one vulnerable direct package, Vite (highest reported severity high). Pinned 6.3.5 → 6.4.6 within major 6; lockfile reviewed, root and clean-clone builds passed, npm audit now reports zero known vulnerabilities. Compiled application assets were byte-identical. See [audit](frontend_dependency_audit.json). |
| Native verification | Existing `run.ps1` loaded both unchanged models; 1,776 prediction + 592 explanation requests and 15 expected invalid cases passed. The separate original 592-profile smoke passed. Owned server stopped after testing. |

The [remote verification receipt](phase3_remote_verification.json) pins the inspected implementation revision. The final audit-record commit changes reports/documentation only. No remote history was rewritten.

## Prepared project and exclusions

The selected name was available; no alternative name or existing-repository overwrite was needed. Intended default branch: `main`. No organization destination, public visibility, force push, paid service or Git LFS is used.

Source folders `backend`, `frontend` (source/lockfiles), `src`, `scripts`, `tests`, `config`, `docs`, normalized `data/metadata`, model metadata/support/importance and research `reports` are prepared for upload. MIT applies to original code/docs only. Raw/processed/interim datasets, native model binaries, prediction-row outputs, source examples/full third-party snapshots, quote evidence, backups, dependencies, build output and local tools are excluded. [Installation](../docs/INSTALLATION.md) explains lawful acquisition, explicit reconstruction and exact artifact restoration.

The first local pre-upload snapshot is preserved on `archive/local-phase2-baseline` and in the Phase 3 checkpoint. Before any upload, individual examples embedded in its registry were removed from the publishable baseline. Its original local history remains preserved; the archive branch is **local only and must not be pushed**. No remote history exists or was rewritten. Use `git push origin main`, never `--all`, to avoid publishing local audit history.

The repository guard scans staged files and all blobs in the intended current branch ancestry for known credential patterns, private paths, row samples and files above 5 MiB. It does not prove absence of every secret or legal risk, so human diff/license review remains required. Final exact scan/blob/test/commit results will be recorded after the last commit.

## Zero-cost CI gate

Private GitHub-hosted compute can incur charges beyond included usage. The billing lookup returned 404 and required an additional `user` scope; no broader access was requested. The user explicitly chose **keep hosted CI gated** because free usage/zero-overage protection is unconfirmed. Repository variables were read back empty; both jobs require `SKYLENS_CI_ZERO_SPEND_CONFIRMED=true`, so they remain skipped. No hosted compute job executed and no billing setting changed. [Official billing rules](https://docs.github.com/en/actions/concepts/billing-and-usage).

Actual inspected runs: [initial backup](https://github.com/SachitBabbar07/skylens-indian-airfare-intelligence/actions/runs/43691265087) and [security-patched source](https://github.com/SachitBabbar07/skylens-indian-airfare-intelligence/actions/runs/43691732763): **skipped**, not passed. The initial run's two job records had no steps executed. The final report commit retains the same gate. Local checks passed independently. Enable hosted execution only after the owner confirms the budget safeguard; this delivery does not request that change again.

## Clone, pull and run

```powershell
git clone https://github.com/SachitBabbar07/skylens-indian-airfare-intelligence.git
cd skylens-indian-airfare-intelligence
git config core.hooksPath .githooks
git pull --ff-only
```

Use Git's secure credential-manager sign-in for private access, or complete standard GitHub CLI web sign-in; never paste tokens into chat. Follow [installation](../docs/INSTALLATION.md) and [contributing](../CONTRIBUTING.md). A clone does not include private datasets/native models or historical machine-local checkpoints.

For future work: create `feature/<name>` or `fix/<name>`, run the relevant portable/full-local checks, review staged content, run the guards, commit, then push that branch normally. Pull with `git pull --ff-only` before starting. The included pre-push hook blocks local archival history and scans each pushed ancestry. No paid API, LFS quota, hosted publication or public visibility is required.
