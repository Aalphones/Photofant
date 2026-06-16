#Requires -Version 5.1
$ErrorActionPreference = 'Stop'
$root = $PSScriptRoot

Write-Host '=== Datenbank-Migration ===' -ForegroundColor Cyan
Push-Location "$root\backend"
uv run alembic upgrade head
if ($LASTEXITCODE -ne 0) { Write-Error 'Migration fehlgeschlagen'; exit 1 }
Pop-Location

Write-Host '=== Backend starten (http://localhost:8000) ===' -ForegroundColor Cyan
$backend = Start-Process `
    -FilePath 'uv' `
    -ArgumentList 'run', 'uvicorn', 'photofant.main:app', '--reload', '--port', '8000' `
    -WorkingDirectory "$root\backend" `
    -NoNewWindow -PassThru

Write-Host '=== Frontend starten (http://localhost:4200) ===' -ForegroundColor Cyan
$frontend = Start-Process `
    -FilePath 'npm' `
    -ArgumentList 'start' `
    -WorkingDirectory "$root\frontend" `
    -NoNewWindow -PassThru

Write-Host ''
Write-Host 'Photofant laeuft:' -ForegroundColor Green
Write-Host '  Backend:  http://localhost:8000'
Write-Host '  Frontend: http://localhost:4200'
Write-Host ''
Write-Host 'Ctrl+C zum Beenden.' -ForegroundColor Yellow

try {
    while (!$backend.HasExited -and !$frontend.HasExited) {
        Start-Sleep -Milliseconds 500
    }
} finally {
    Write-Host ''
    Write-Host 'Beende Photofant...' -ForegroundColor Yellow
    # /T kills the entire process tree — needed for uvicorn --reload which spawns a child watcher
    if (!$backend.HasExited) { $null = taskkill /T /F /PID $backend.Id }
    if (!$frontend.HasExited) { $null = taskkill /T /F /PID $frontend.Id }
}
