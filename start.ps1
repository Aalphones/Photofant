#Requires -Version 5.1
$ErrorActionPreference = 'Stop'
$root = $PSScriptRoot

# .env.local einlesen (KEY=VALUE), bevor irgendetwas startet — Kindprozesse
# (alembic, uvicorn, npm) erben die hier gesetzten Variablen.
$envFile = Join-Path $root '.env.local'
if (Test-Path $envFile) {
    Write-Host '=== Lade .env.local ===' -ForegroundColor Cyan
    foreach ($line in Get-Content $envFile) {
        $trimmed = $line.Trim()
        if ($trimmed -eq '' -or $trimmed.StartsWith('#')) { continue }
        $pair = $trimmed -split '=', 2
        if ($pair.Count -ne 2) { continue }
        $key = $pair[0].Trim()
        $value = $pair[1].Trim().Trim('"').Trim("'")
        if ($key) {
            Set-Item -Path "env:$key" -Value $value
            Write-Host "  $key=$value"
        }
    }
}

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
    -FilePath 'npm.cmd' `
    -ArgumentList 'start' `
    -WorkingDirectory "$root\frontend" `
    -NoNewWindow -PassThru

Write-Host ''
Write-Host 'Photofant laeuft:' -ForegroundColor Green
Write-Host '  Backend:  http://localhost:8000'
Write-Host '  Frontend: http://localhost:4200'
Write-Host ''

# Warte auf Frontend, dann Browser oeffnen
$frontendUrl = 'http://localhost:4200'
Write-Host 'Warte auf Frontend...' -ForegroundColor Cyan
$deadline = (Get-Date).AddSeconds(90)
$browserOpened = $false
while ((Get-Date) -lt $deadline -and !$frontend.HasExited) {
    try {
        $null = Invoke-WebRequest -Uri $frontendUrl -UseBasicParsing -TimeoutSec 2 -ErrorAction Stop
        Start-Process $frontendUrl
        Write-Host 'Browser geoeffnet.' -ForegroundColor Green
        $browserOpened = $true
        break
    } catch {
        Start-Sleep -Milliseconds 800
    }
}
if (!$browserOpened) {
    Write-Host "Frontend nicht erreichbar — $frontendUrl manuell oeffnen." -ForegroundColor Yellow
}

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
