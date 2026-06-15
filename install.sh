#!/usr/bin/env bash
# Photofant — Dependencies installieren (idempotent, beliebig oft ausfuehrbar).
# Voraussetzungen: uv (https://docs.astral.sh/uv/), Node 20+ mit npm
set -euo pipefail
cd "$(dirname "$0")"

echo "=== Backend: uv sync ==="
(cd backend && uv sync --dev)

echo "=== Frontend: npm ci ==="
(cd frontend && npm ci)

echo ""
echo "Installation abgeschlossen. Weiter mit: ./start.sh"
