# GitHub delivery status

Local version control is initialized at `D:\SkyLens` on `main`. GitHub CLI v2.104.0 was obtained from the official CLI release and checked against its published SHA-256. Initial `gh auth status` reported no authenticated host. The GitHub integration was installed during the session, but no GitHub repository tool is exposed to this running chat. The user chose secure CLI sign-in; completion has not yet been observed.

**Remote repository, owner, visibility, URL, push and GitHub Actions results are not yet verified.** No repository URL is invented and no completion tag has been created. This report will be updated if authentication becomes available. The mandatory GitHub delivery is pending authentication, not marked complete.

## Prepared project and exclusions

The intended name is `skylens-indian-airfare-intelligence`, private under the authenticated personal account, default branch `main`. Check availability before creation; preserve any existing repository and choose an alternate name if necessary. No organization destination, public visibility, force push, paid service or Git LFS is authorized.

Source folders `backend`, `frontend` (source/lockfiles), `src`, `scripts`, `tests`, `config`, `docs`, normalized `data/metadata`, model metadata/support/importance and research `reports` are prepared for upload. MIT applies to original code/docs only. Raw/processed/interim datasets, native model binaries, prediction-row outputs, source examples/full third-party snapshots, quote evidence, backups, dependencies, build output and local tools are excluded. [Installation](../docs/INSTALLATION.md) explains lawful acquisition, explicit reconstruction and exact artifact restoration.

The first local pre-upload snapshot is preserved on `archive/local-phase2-baseline` and in the Phase 3 checkpoint. Before any upload, individual examples embedded in its registry were removed from the publishable baseline. Its original local history remains preserved; the archive branch is **local only and must not be pushed**. No remote history exists or was rewritten. Use `git push origin main`, never `--all`, to avoid publishing local audit history.

The repository guard scans staged files and all blobs in the intended current branch ancestry for known credential patterns, private paths, row samples and files above 5 MiB. It does not prove absence of every secret or legal risk, so human diff/license review remains required. Final exact scan/blob/test/commit results will be recorded after the last commit.

## Secure sign-in and remaining remote work

In PowerShell run `D:\SkyLens\.tools\gh\bin\bin\gh.exe auth login --hostname github.com --git-protocol https --web`, complete GitHub's own browser/device flow and then `auth status`. Never put a token in chat or an `.env` committed to Git. Once authenticated, check the user's identity/name availability, create the private repository, verify ownership/visibility, add `origin`, scan/push `main`, verify the remote commit/default branch/README/docs and inspect the actual Actions run. A configured workflow is not a passed workflow.

Clone instructions require the actual verified URL; none is supplied until creation succeeds. Once cloned, use `git pull --ff-only` for updates and follow [installation](../docs/INSTALLATION.md) and [contributing](../CONTRIBUTING.md). A clone does not include private datasets/native models or historical machine-local checkpoints.
