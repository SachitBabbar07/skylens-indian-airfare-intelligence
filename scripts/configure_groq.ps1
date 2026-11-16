$ErrorActionPreference = 'Stop'

if ((Read-Host 'Is this a key from a Groq Free plan? Type YES to continue') -cne 'YES') {
    throw 'Use a key from an active Groq Free plan for this project.'
}

$workspace = (Resolve-Path -LiteralPath (Join-Path $PSScriptRoot '..')).Path
$envPath = Join-Path $workspace '.env'
$temporaryPath = Join-Path $workspace ('.env.' + [Guid]::NewGuid().ToString('N'))
$secret = Read-Host 'Enter the replacement Groq API key' -AsSecureString
$buffer = [Runtime.InteropServices.Marshal]::SecureStringToBSTR($secret)
try {
    $key = [Runtime.InteropServices.Marshal]::PtrToStringBSTR($buffer).Trim()
    if ($key -cnotmatch '^gsk_[A-Za-z0-9_-]{32,}$') {
        throw 'The value entered is not in the expected Groq API key format.'
    }
    $lines = @()
    if ([IO.File]::Exists($envPath)) {
        $lines = @([IO.File]::ReadAllLines($envPath) | Where-Object {
            $_ -notmatch '^\s*(?:export\s+)?GROQ_(?:API_KEY|FREE_PLAN_CONFIRMED)\s*='
        })
    }
    $lines += 'GROQ_API_KEY=' + $key
    $lines += 'GROQ_FREE_PLAN_CONFIRMED=true'
    [IO.File]::WriteAllLines($temporaryPath, [string[]] $lines, [Text.UTF8Encoding]::new($false))
    if ([IO.File]::Exists($envPath)) {
        [IO.File]::Replace($temporaryPath, $envPath, [NullString]::Value)
    } else {
        [IO.File]::Move($temporaryPath, $envPath)
    }
    Write-Host 'Saved Groq Free plan configuration to the ignored local .env file.'
} finally {
    [Runtime.InteropServices.Marshal]::ZeroFreeBSTR($buffer)
    $secret.Dispose()
    Remove-Variable -Name key,lines -ErrorAction SilentlyContinue
    if ([IO.File]::Exists($temporaryPath)) { [IO.File]::Delete($temporaryPath) }
}
