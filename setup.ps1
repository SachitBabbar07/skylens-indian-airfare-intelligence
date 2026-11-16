$ErrorActionPreference = 'Stop'
Set-Location -LiteralPath $PSScriptRoot
if (-not (Test-Path -LiteralPath '.venv\Scripts\python.exe')) {
    uv venv .venv --python 3.12
    if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }
}
uv pip sync --python .venv\Scripts\python.exe requirements.txt
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }
npm --prefix frontend ci --no-fund
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }
npm --prefix frontend run build
exit $LASTEXITCODE
