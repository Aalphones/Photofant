@echo off
REM Photofant — Dependencies installieren (idempotent, beliebig oft ausfuehrbar).
REM Voraussetzungen: uv (https://docs.astral.sh/uv/), Node 20+ mit npm
setlocal enabledelayedexpansion

echo === Backend: uv sync ===
pushd backend
uv sync --dev
if !errorlevel! neq 0 (
    echo FEHLER: Backend-Installation fehlgeschlagen.
    exit /b 1
)
popd

echo === Frontend: npm ci ===
pushd frontend
call npm ci
if !errorlevel! neq 0 (
    echo FEHLER: Frontend-Installation fehlgeschlagen.
    exit /b 1
)
popd

echo.
echo Installation abgeschlossen. Weiter mit: start.cmd
exit /b 0
