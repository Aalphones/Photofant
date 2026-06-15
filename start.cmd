@echo off
REM Photofant starten — Backend (http://localhost:8000) + Frontend (http://localhost:4200)
REM Voraussetzung: install.cmd wurde ausgefuehrt.
setlocal enabledelayedexpansion

echo === Datenbank-Migration ===
pushd backend
uv run alembic upgrade head
if !errorlevel! neq 0 (
    echo FEHLER: Alembic-Migration fehlgeschlagen.
    exit /b 1
)
popd

echo === Backend starten (http://localhost:8000) ===
start "Photofant Backend" cmd /k "cd /d %~dp0backend && uv run uvicorn photofant.main:app --reload --port 8000"

echo === Frontend starten (http://localhost:4200) ===
start "Photofant Frontend" cmd /k "cd /d %~dp0frontend && npm start"

echo.
echo Photofant laeuft:
echo   Backend:  http://localhost:8000
echo   Frontend: http://localhost:4200
echo.
echo Fenster schliessen zum Beenden.
exit /b 0
