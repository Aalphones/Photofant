#Requires -Version 5.1
$ErrorActionPreference = 'Stop'
$root = $PSScriptRoot

# Alle Konfiguration lebt in Data\.photofant\settings.json (siehe backend\settings.example.json).
# Einziger Override-Hebel: Env-Var PHOTOFANT_SETTINGS_PATH (CI/Docker).

Write-Host '=== Datenbank-Migration ===' -ForegroundColor Cyan
Write-Host '  (Beim ersten Start baut uv die Python-Umgebung - das kann einige Minuten dauern.)' -ForegroundColor DarkGray
Push-Location "$root\backend"
uv run alembic upgrade head
if ($LASTEXITCODE -ne 0) { Write-Error 'Migration fehlgeschlagen'; exit 1 }
Pop-Location

Write-Host '=== Backend starten (http://localhost:8000) ===' -ForegroundColor Cyan
# --reload-dir photofant: nur den Paketordner ueberwachen, NICHT den ganzen
# backend-Baum. Sonst watcht uvicorn auch .venv (zigtausend Dateien) und tests/
# - auf Windows reisst der File-Watcher dort reproduzierbar ab und nimmt uvicorn
# mit, was den Watchdog unten alles abschiessen laesst.
$backend = Start-Process `
    -FilePath 'uv' `
    -ArgumentList 'run', 'uvicorn', 'photofant.main:app', '--reload', '--reload-dir', 'photofant', '--port', '8000' `
    -WorkingDirectory "$root\backend" `
    -NoNewWindow -PassThru

# --host 0.0.0.0: Dev-Server lauscht auf allen Netzwerk-Adressen (nicht nur
# localhost), damit andere Geraete im LAN das Frontend erreichen. Das Backend
# bleibt auf localhost - der Dev-Proxy (proxy.conf.json) reicht /api intern weiter.
Write-Host '=== Frontend starten (http://127.0.0.1:4200, LAN-weit) ===' -ForegroundColor Cyan
$frontend = Start-Process `
    -FilePath 'npm.cmd' `
    -ArgumentList 'start', '--', '--host', '0.0.0.0' `
    -WorkingDirectory "$root\frontend" `
    -NoNewWindow -PassThru

Write-Host ''
Write-Host 'Photofant laeuft:' -ForegroundColor Green
Write-Host '  Backend:  http://localhost:8000'
Write-Host '  Frontend: http://127.0.0.1:4200'
Write-Host '  Im LAN:   http://192.168.178.51:4200' -ForegroundColor Green
Write-Host ''

# Warte auf Frontend, dann Browser oeffnen
$frontendUrl = 'http://127.0.0.1:4200'
Write-Host 'Warte auf Frontend (Angular kompiliert beim ersten Mal ~30-60s)...' -ForegroundColor Cyan
$deadline = (Get-Date).AddSeconds(90)
$startedAt = Get-Date
$browserOpened = $false
while ((Get-Date) -lt $deadline -and !$frontend.HasExited) {
    try {
        $null = Invoke-WebRequest -Uri $frontendUrl -UseBasicParsing -TimeoutSec 2 -ErrorAction Stop
        # \r ueberschreibt die Heartbeat-Zeile, bevor die Erfolgsmeldung kommt
        Write-Host "`r                                             " -NoNewline
        Write-Host "`rBrowser geoeffnet." -ForegroundColor Green
        Start-Process $frontendUrl
        $browserOpened = $true
        break
    } catch {
        # Heartbeat: verstrichene Sekunden in-place anzeigen, damit es nicht
        # eingefroren wirkt. -NoNewline + \r ueberschreibt dieselbe Zeile.
        $elapsed = [int]((Get-Date) - $startedAt).TotalSeconds
        Write-Host ("`r  ...warte seit {0,3}s (Timeout bei 90s)" -f $elapsed) -NoNewline -ForegroundColor DarkGray
        Start-Sleep -Milliseconds 800
    }
}
if (!$browserOpened) {
    Write-Host ''  # Heartbeat-Zeile sauber abschliessen
    Write-Host "Frontend nicht erreichbar - $frontendUrl manuell oeffnen." -ForegroundColor Yellow
}

Write-Host ''
Write-Host 'Ctrl+C zum Beenden.' -ForegroundColor Yellow

try {
    while (!$backend.HasExited -and !$frontend.HasExited) {
        Start-Sleep -Milliseconds 500
    }
    # Wer ist gekippt? Festhalten, statt stumm alles abzuschiessen - damit ein
    # unerwarteter Abbruch nachvollziehbar ist und nicht geraten werden muss.
    if ($backend.HasExited) {
        Write-Host "Backend ist beendet (ExitCode $($backend.ExitCode)) - fahre Frontend mit herunter." -ForegroundColor Red
    } else {
        Write-Host "Frontend ist beendet (ExitCode $($frontend.ExitCode)) - fahre Backend mit herunter." -ForegroundColor Red
    }
} finally {
    Write-Host ''
    Write-Host 'Beende Photofant...' -ForegroundColor Yellow
    # /T kills the entire process tree - needed for uvicorn --reload which spawns a child watcher
    if (!$backend.HasExited) { $null = taskkill /T /F /PID $backend.Id }
    if (!$frontend.HasExited) { $null = taskkill /T /F /PID $frontend.Id }
}
