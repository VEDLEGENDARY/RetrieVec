# Requires Docker Desktop with Linux containers; no host language runtimes needed.
[CmdletBinding()]
param([ValidateSet('start', 'doctor', 'status', 'logs', 'stop')][string]$Action = 'start')
$ErrorActionPreference = 'Stop'
Set-StrictMode -Version Latest
Set-Location -LiteralPath $PSScriptRoot

function Invoke-Compose {
    param([string[]]$ComposeArguments)
    & docker compose -f "$PSScriptRoot/compose.yaml" @ComposeArguments
    if ($LASTEXITCODE -ne 0) { throw "Docker Compose failed. Run .\start.ps1 logs to inspect startup, then retry .\start.ps1." }
}

try {
    if (-not (Get-Command docker -ErrorAction SilentlyContinue)) {
        throw 'Docker is missing. Install Docker Desktop, start it, and select Linux containers. Then rerun .\start.ps1.'
    }
    & docker compose version
    if ($LASTEXITCODE -ne 0) { throw 'Docker Compose is unavailable. Update Docker Desktop or install the Compose plugin, then retry.' }
    $ErrorActionPreference = 'Continue'
    $engineType = & docker info --format '{{.OSType}}' 2>$null
    $engineExit = $LASTEXITCODE
    $ErrorActionPreference = 'Stop'
    if ($engineExit -ne 0) { throw 'Docker is not running. Start Docker Desktop, wait for the engine, and rerun .\start.ps1.' }
    if ($engineType -ne 'linux') { throw 'This workspace uses Linux containers. Switch Docker Desktop to Linux containers and retry.' }
    Invoke-Compose -ComposeArguments @('config', '--quiet')
    switch ($Action) {
        'doctor' { Write-Host 'Docker, Linux containers, and Compose configuration are ready. Start with .\start.ps1.' }
        'status' { Invoke-Compose -ComposeArguments @('ps', '-a') }
        'logs' { Invoke-Compose -ComposeArguments @('logs', '--tail=100', 'workspace', 'identity', 'postgres', 'init') }
        'stop' { Invoke-Compose -ComposeArguments @('down'); Write-Host 'Stopped. Your account, papers, and model cache are preserved. Run .\start.ps1 to return.' }
        'start' {
            Write-Host 'Starting RetrieVec. The first build and retrieval model download may take several minutes.'
            Write-Host 'Ports 8000 and 8080 must be free. Startup waits for the workspace and sign-in service.'
            Invoke-Compose -ComposeArguments @('up', '--build', '--wait', '--wait-timeout', '900')
            Write-Host "`nOpen http://127.0.0.1:8000. Choose Sign in, then Register to create your local account."
            Write-Host 'Try the SciFact starter, or create a private collection and upload your papers.'
        }
    }
} catch {
    Write-Host "`n$($_.Exception.Message)" -ForegroundColor Red
    exit 1
}
