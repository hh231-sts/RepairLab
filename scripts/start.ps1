param([switch]$SkipImageBuild, [switch]$EnableModelCalls, [switch]$SkipSetup)
$ErrorActionPreference = 'Stop'
$projectRoot = Split-Path -Parent $PSScriptRoot
Set-Location -LiteralPath $projectRoot
$env:UV_CACHE_DIR = Join-Path $projectRoot '.cache/uv'
$env:npm_config_cache = Join-Path $projectRoot '.cache/npm'
$env:MODEL_CALLS_ENABLED = if ($EnableModelCalls) { 'true' } else { 'false' }
$env:EMBEDDING_ENABLED = 'false'
$env:LANGSMITH_TRACING = 'false'
if (!(Test-Path -LiteralPath '.env')) { Copy-Item -LiteralPath '.env.example' -Destination '.env' }
New-Item -ItemType Directory -Force -Path 'data' | Out-Null
if (Test-Path -LiteralPath 'data/processes.json') { throw 'Process manifest exists. Run scripts/stop.ps1 before starting again.' }
if (!$SkipSetup) {
    uv sync --frozen --extra dev
    if ($LASTEXITCODE -ne 0) { throw 'Python dependency setup failed' }
}
$pythonExe = Join-Path $projectRoot '.venv/Scripts/python.exe'
if (!(Test-Path -LiteralPath $pythonExe)) { throw 'Python environment missing. Start without -SkipSetup.' }
& $pythonExe -m repairlab.cli check-config
if ($LASTEXITCODE -ne 0) { throw 'Model configuration incomplete; check .env without sharing the key.' }
docker compose up -d --wait db
if ($LASTEXITCODE -ne 0) { throw 'PostgreSQL startup failed' }
if (!$SkipImageBuild) {
    docker build -f docker/sandbox.Dockerfile -t repairlab-sandbox:local .
    if ($LASTEXITCODE -ne 0) { throw 'Sandbox image build failed' }
}
& $pythonExe -c 'from repairlab.config import Settings; Settings().prepare()'
& $pythonExe -m alembic upgrade head
if ($LASTEXITCODE -ne 0) { throw 'Database migration failed' }
if (!$SkipSetup) {
    Push-Location -LiteralPath 'frontend'
    try {
    npm.cmd ci
    if ($LASTEXITCODE -ne 0) { throw 'Frontend dependencies failed' }
    npm.cmd run build
    if ($LASTEXITCODE -ne 0) { throw 'Frontend build failed' }
    } finally { Pop-Location }
}
$apiProcess = Start-Process -FilePath $pythonExe -ArgumentList '-m','uvicorn','repairlab.api:create_app','--factory','--host','127.0.0.1','--port','8000' -WorkingDirectory $projectRoot -WindowStyle Hidden -PassThru -RedirectStandardOutput 'data/api.log' -RedirectStandardError 'data/api.error.log'
$workerProcess = Start-Process -FilePath $pythonExe -ArgumentList '-m','repairlab.cli','worker' -WorkingDirectory $projectRoot -WindowStyle Hidden -PassThru -RedirectStandardOutput 'data/worker.log' -RedirectStandardError 'data/worker.error.log'
$viteEntry = Join-Path $projectRoot 'frontend/node_modules/vite/bin/vite.js'
$nodeExe = (Get-Command node.exe).Source
$uiProcess = Start-Process -FilePath $nodeExe -ArgumentList ('"' + $viteEntry + '"'),'--host','127.0.0.1','--port','5173' -WorkingDirectory (Join-Path $projectRoot 'frontend') -WindowStyle Hidden -PassThru -RedirectStandardOutput (Join-Path $projectRoot 'data/ui.log') -RedirectStandardError (Join-Path $projectRoot 'data/ui.error.log')
@(@{pid=$apiProcess.Id;name='api'},@{pid=$workerProcess.Id;name='worker'},@{pid=$uiProcess.Id;name='ui'}) | ConvertTo-Json | Set-Content -LiteralPath 'data/processes.json' -Encoding UTF8
Write-Host 'RepairLab: http://localhost:5173  API: http://127.0.0.1:8000/docs'
Write-Host ('Real model mode: ' + $EnableModelCalls + '. Embedding stays OFF. Logs: data/*.log')
