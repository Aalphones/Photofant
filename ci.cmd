@echo off
REM Photofant CI — Lint + Tests fuer alles, was existiert.
REM Wird mit Stage 0 (Backend-/Frontend-Skelett) scharf geschaltet.
setlocal enabledelayedexpansion
set FAILED=0

if exist backend\pyproject.toml (
    echo === Backend: ruff ===
    pushd backend
    uv run ruff check . || set FAILED=1
    echo === Backend: pytest ===
    uv run pytest || set FAILED=1
    popd
) else (
    echo [skip] backend\ existiert noch nicht
)

if exist frontend\package.json (
    pushd frontend
    echo === Frontend: lint ===
    call npm run lint || set FAILED=1
    echo === Frontend: build ===
    call npm run build || set FAILED=1
    echo === Frontend: test ===
    call npm test -- --watch=false || set FAILED=1
    popd
) else (
    echo [skip] frontend\ existiert noch nicht
)

if !FAILED! neq 0 (
    echo CI: FAILED
    exit /b 1
)
echo CI: OK
exit /b 0
