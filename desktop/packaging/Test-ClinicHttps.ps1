# Read-only. Uses OS certificate chain and hostname validation; no bypass option.
param([Parameter(Mandatory)][uri]$Origin)
$ErrorActionPreference = 'Stop'
if ($Origin.Scheme -ne 'https' -or $Origin.UserInfo -or $Origin.Query -or $Origin.Fragment -or $Origin.AbsolutePath -ne '/') {
    throw 'Provide a bare HTTPS origin without credentials'
}
foreach ($path in @('/api/health', '/api/health/ready')) {
    $reply = Invoke-RestMethod -Uri ($Origin.GetLeftPart('Authority') + $path) -TimeoutSec 5
    if ($reply.status -notin @('ok','ready')) { throw 'Health check failed' }
}
Write-Output 'PASS: trusted HTTPS liveness and database readiness'
