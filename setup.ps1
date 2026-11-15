$ErrorActionPreference = 'Stop'
Set-Location -LiteralPath $PSScriptRoot
uv venv .venv --python 3.12
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }
uv pip install --python .venv\Scripts\python.exe -r requirements.txt
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }
npm --prefix frontend ci --no-fund
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }
npm --prefix frontend run build
exit $LASTEXITCODE
