$ErrorActionPreference = 'Stop'
$projectRoot = (Resolve-Path -LiteralPath (Split-Path -Parent $PSScriptRoot)).Path
$manifest = Join-Path $projectRoot 'data/processes.json'
if (!(Test-Path -LiteralPath $manifest)) { Write-Host 'No owned process manifest.'; exit 0 }
$ownedProcesses = Get-Content -LiteralPath $manifest -Raw | ConvertFrom-Json
foreach ($owned in $ownedProcesses) {
    $process = Get-CimInstance Win32_Process -Filter ("ProcessId = " + [int]$owned.pid)
    if ($null -ne $process) {
        # Protect against PID reuse: stop only commands rooted in this project.
        if ($process.ExecutablePath.StartsWith($projectRoot, [StringComparison]::OrdinalIgnoreCase) -or ($process.CommandLine -and $process.CommandLine.Contains($projectRoot))) {
            Stop-Process -Id $owned.pid
        } else { throw ('PID no longer belongs to this project: ' + $owned.pid) }
    }
}
Remove-Item -LiteralPath $manifest
Write-Host 'API, worker and UI stopped. Database and execution artifacts are preserved.'
