# P8b — ComfyUI-Workflow-Integration (Stage 5, koexistierend)

> Status: geparkt · **optional** · Quelle: [Konzept-ComfyUI-Integration](../../Konzept-ComfyUI-Integration.md) · Abhängigkeiten: P2 (Galerie + Job-Queue), P4 (Settings/Registry-Pattern), P8 (Versionierung, `personX/edits/`, Import-Hook) · **koexistiert mit P9** (in-process GenerativeEngine), ersetzt es nicht.

Photofant **triggert** Workflows, ComfyUI **führt aus**. Fire-and-Forget: Ergebnis landet in ComfyUIs eigenem `output/`, wird **dort** reviewt, und nur bei Bedarf als Edit zurück importiert (bewusstes Speichern, §8.2-Prinzip aus P8). Kein torch/diffusers-Stack — ComfyUI besitzt Modelle, VRAM, GGUF/fp8. Dieser Pfad steht **neben** dem in-process-Backend aus P9; ADR-003 dokumentiert die Koexistenz und das Verhältnis zu ADR-002.

## Overview

| Phase | Topic | Rating | Status |
|---|---|---|---|
| 1 | [Verbindung & Settings (ADR-003)](phase-1-verbindung-settings.md) | standard | complete |
| 2 | [Workflow-Template-Registry](phase-2-workflow-registry.md) | heikel | complete |
| 3 | [Trigger-Flow (Fire-and-Forget)](phase-3-trigger-flow.md) | heikel | pending |
| 4 | [Galerie-Run-Leiste (Armed-Slots, Batch)](phase-4-run-leiste.md) | heikel | pending |
| 5 | [Import als Edit (on demand)](phase-5-import-edit.md) | standard | pending |

## Kontrakt (Backend ↔ Frontend)

- **Settings:** `GET/PUT /api/settings/comfyui` — `{ enabled, base_url, client_id, output_dir, timeout }`; **`POST /api/comfyui/test-connection`** → Passthrough `GET /system_stats`, Antwort `{ ok, detail }` mit Fehlerklasse (was erwartet / was gefunden / nächster Schritt). Trigger bleiben gegated, bis `enabled && Verbindung ok`.
- **Workflows (CRUD in Settings):** `GET/POST/PATCH/DELETE /api/comfyui/workflows` — Config nach Konzept §2.1 (`id, name, category, template_path, inputs[], params[]`); **`POST /api/comfyui/workflows/introspect`** — Template (API-Format-JSON) rein → Liste aller Nodes mit `_meta.title` + `class_type` + Vorschlag erkannter Bild-Eingänge. Aktivierung erst nach Validierung (Titel existiert **und** eindeutig, `field` existiert, mind. ein `SaveImage`).
- **Trigger:** **`POST /api/comfyui/workflows/{id}/run`** — `{ inputs: { <key>: asset_id | asset_id[] }, params: { <key>: value } }` → legt **N Jobs** in die bestehende Queue (genau **eine** Batch-Achse = der Array-Input), je Job `deepcopy` des Templates → `POST /upload/image` → Patch → `POST /prompt`; Antwort `{ jobs: [{ job_id, prompt_id }] }`. Status über bestehende SSE-Strecke; **kein** Auto-Zurückschreiben.
- **Import (on demand):** **`GET /api/comfyui/results`** — `?prompt_id=` (über `GET /history/{id}` → `outputs` → `GET /view`) **oder** lokal aus `output_dir`; **Übernahme** über den **bestehenden P8-Hook** `POST /api/assets/{id}/versions/import` mit `type = comfyui`, Lineage zum Quell-Asset, Versionskette wie in P8.

## Finale Akzeptanzkriterien

1. ComfyUI-Verbindung in Settings konfigurierbar; „Verbindung testen" liefert klare Erfolg-/Fehler-Meldung (Fehlerklasse §12.2a); Trigger gegated bis Verbindung steht. ADR-003 dokumentiert die Koexistenz mit dem in-process-Pfad (Querverweis ADR-002).
2. Workflow im **API-Format** hochladbar, introspektiert (Titel als Name-Hooks, Dropdown statt Abtippen), Inputs (1..x) + Params (0..x) gebunden **über `_meta.title`** (Node-ID nur Fallback), validiert, aktivierbar; invalide/unvalidierte Workflows bleiben gegated und erscheinen nicht im Run-Dropdown.
3. Galerie-Run-Leiste: Workflow wählen → Slots erscheinen → Slot „scharf schalten" → Galerie-Klick bindet Bild; Feuer-Button aktiv ab allen Pflicht-Slots, zeigt die Anzahl („Feuern (12×)"). Konstante bleibt gebunden, nur variabler Slot wird neu gewählt; optional 🔒.
4. Batch über **genau eine** Achse (Multi-Select per Strg/Shift/Long-Press); zweite Multi-Select **verschiebt** die Achse statt Kreuzprodukt; `kind = mask` ist nicht batchbar. N Jobs in der Queue, alle Ergebnisse in ComfyUIs `output/`.
5. Import on demand: Ergebnisse aus `/history` bzw. `output_dir` listbar; gewähltes Bild landet als **Edit** in `personX/edits/` mit Versionskette + Lineage zum Quell-Asset (P8-Hook, `type = comfyui`). Ohne Import rührt Photofant nichts an.
6. Koexistenz sauber: ComfyUI-Pfad gegated parallel zu P9; ohne ComfyUI-Verbindung ist der Rest der App unbeeinträchtigt. **Offline-Garantie gewahrt** — nur Verkehr zur konfigurierten (Default lokalen) Instanz.

## Smoke-Checkliste (User, am Plan-Ende)

- [ ] ComfyUI lokal starten → in Settings `base_url` setzen → „Verbindung testen" grün; absichtlich falscher Port → klare Fehlermeldung
- [ ] Upscale-Workflow (API-Format, ein `LoadImage` mit Titel „Source", endet auf `SaveImage`) hochladen → Introspektion schlägt Input „Source" vor → aktivieren
- [ ] Workflow ohne `SaveImage` hochladen → Validierung blockt mit klarer Meldung
- [ ] Run-Leiste: Bild an „Source" binden → feuern → Lauf erscheint in ComfyUIs Queue, Ergebnis in `output/photofant/...`
- [ ] Multi-Subject-Workflow: Referenz an Slot 1 (Konstante), 12 Bilder per Multi-Select an Slot 2 → „Feuern (12×)" → 12 Jobs, Referenz über alle gleich
- [ ] Ein Ergebnis aus dem Output importieren → liegt als Edit-Version im Person-Ordner, Lineage zeigt Quell-Asset

## Summary

## Files touched

## Commits

## Deviations from plan

## Follow-ups

- `kind = mask`-Slots brauchen den Masken-Editor, der erst in **P9 Phase 4** (Inpainting) entsteht. Solange P9 Ph4 nicht steht, sind Masken-Workflows in der Run-Leiste gegated (siehe Phase 4). Bei Bedarf minimalen Masken-Editor vorziehen.
