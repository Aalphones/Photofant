#!/usr/bin/env bash
# Photofant starten — Backend (http://localhost:8000) + Frontend (http://localhost:4200)
# Voraussetzung: ./install.sh wurde ausgefuehrt.
set -euo pipefail
cd "$(dirname "$0")"

echo "=== Datenbank-Migration ==="
(cd backend && uv run alembic upgrade head)

echo "=== Backend starten (http://localhost:8000) ==="
(cd backend && uv run uvicorn photofant.main:app --reload --port 8000) &
BACKEND_PID=$!

echo "=== Frontend starten (http://localhost:4200) ==="
(cd frontend && npm start) &
FRONTEND_PID=$!

echo ""
echo "Photofant laeuft:"
echo "  Backend:  http://localhost:8000"
echo "  Frontend: http://localhost:4200"
echo ""
echo "Ctrl+C zum Beenden."

cleanup() {
    echo ""
    echo "Beende Photofant..."
    kill "$BACKEND_PID" "$FRONTEND_PID" 2>/dev/null || true
}
trap cleanup EXIT INT TERM
wait
