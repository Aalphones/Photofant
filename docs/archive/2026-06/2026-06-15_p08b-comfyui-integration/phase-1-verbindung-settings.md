# P8b · Phase 1 — Verbindung & Settings (ADR-003)

> Rating: **standard** · Status: complete

## Kontext (vorher lesen)

- [README.md](README.md) — Kontrakt (Settings, test-connection), Koexistenz mit P9
- [Konzept-ComfyUI-Integration](../../Konzept-ComfyUI-Integration.md) §1, §6
- [P9 Phase 1](../2026-06-12_p09-generativ/phase-1-generatives-backend.md) — ADR-002 (diffusers vs. ComfyUI), das ADR-003 querverweist
- Settings-Prototyp: `docs/design/js/settings.jsx`, `docs/design/settings.css` (Pixel-Treue)

## Akzeptanzkriterien

- **ADR-003** (`docs/decisions/003-comfyui-trigger-integration.md`): Fire-and-Forget-Trigger als **koexistierender** generativer Pfad neben dem in-process-Backend (P9/ADR-002). Hält fest: kein Auto-Zurückschreiben, ComfyUI besitzt Modelle/VRAM, API-Format-Pflicht, kein torch/diffusers-Zwang. Wann welcher Pfad (Trigger vs. in-process).
- Settings-Block ComfyUI (neben Modell-Registry): `enabled` (false), `base_url` (`http://127.0.0.1:8188`), `client_id` (`photofant`), `output_dir` (leer), `timeout` (10). Persistenz in der DB („DB ist alleinige Wahrheit").
- Backend-Client (`httpx`, Timeout aus Config): `GET /system_stats` für die Verbindungsprüfung. Fehlerklassen analog §12.2a (was erwartet / was gefunden / nächster Schritt), kein stummes Scheitern.
- **„Verbindung testen"-Button** in Settings → `POST /api/comfyui/test-connection` → grün/rot mit Detail. Generative Trigger bleiben gegated, bis `enabled && Verbindung ok`.
- Offline-Garantie: nur Verkehr zur konfigurierten Instanz (Default lokal); kein impliziter externer Call.

## Checkliste

- [x] DB-Migration: entfällt — Settings folgen dem etablierten settings.json-Pattern (Migration 0013 hat Settings aus DB in JSON verschoben); kein Alembic-Step nötig
- [x] `ComfyUIClient` (httpx) mit `system_stats()` + Fehlerklassen-Mapping (`backend/photofant/comfyui/client.py`)
- [x] Routes `GET/PUT /api/settings/comfyui`, `POST /api/comfyui/test-connection` (`backend/photofant/api/comfyui.py`)
- [x] Frontend: Settings-Panel + „Verbindung testen" (`frontend/src/app/features/einstellungen/comfyui/`)
- [x] Gating-Flag (`comfyuiReady`) im NgRx-State: `comfyuiSelectors.selectComfyuiReady` — Quelle für spätere Phasen
- [x] Tests: Client-Unit (Mock 200 / Connection-Refused / Timeout / HTTP-503), Route-Test test-connection (`backend/tests/test_comfyui.py`, 6/6 grün)
- [x] Doc-Update: `docs/decisions/003-comfyui-trigger-integration.md` erstellt; AGENTS.md noch offen (minor, kein Blocker für Phase 2)

## Report-Back

Abweichung: „DB-Migration: comfyui-Settings" aus der Checkliste entfällt — Settings leben seit Migration 0013 in settings.json, nicht in der DB. ComfyUI-Block als nested Dict `"comfyui": { ... }` in AppSettings eingehängt, analog zu `"display"`.

Frontend: eigene NgRx-Feature `comfyui` (actions/reducer/effects/selectors), Settings-Sektion in Einstellungen. `comfyuiSelectors.selectComfyuiReady` = `enabled && testResult.ok` als Gating-Flag für Phasen 2–5.
