# P8b · Phase 5 — Import als Edit (on demand)

> Rating: **standard** (hängt sich an den bestehenden P8-Import-Hook) · Status: pending

## Kontext (vorher lesen)

- [README.md](README.md) — Kontrakt (results, Import über P8-Hook)
- [Konzept-ComfyUI-Integration](../../Konzept-ComfyUI-Integration.md) §4, §6
- [P8 Phase 4](../2026-06-12_p08-editor-cpu/phase-4-versionierung.md) + [P8 README](../2026-06-12_p08-editor-cpu/README.md) — `versions/import`, `VersionDto`, `personX/edits/`, Lineage

## Akzeptanzkriterien

- **`GET /api/comfyui/results`** listet Ergebnisse: über `GET /history/{prompt_id}` → `outputs` → `GET /view`, **oder** bei lokalem Lauf direkt aus `output_dir` (Backend hat FS-Zugriff). Vorschau-URLs für die Auswahl-UI.
- **Übernahme** ausschließlich über den **bestehenden P8-Hook** `POST /api/assets/{id}/versions/import` — neuer `type = comfyui`, `parent_id`-Kette + Lineage zum Quell-Asset, Ablage in `personX/edits/`, `is_current`-Verhalten wie P8. **Kein eigener Schreibpfad** neben P8.
- Bewusstes Speichern: vor dem Import rührt Photofant nichts an; der Import ist der explizite Schritt (§4, deckt sich mit §8.2 aus P8).
- Neue Edit-Version durchläuft die P8-Nachverarbeitung (Tags/Caption-Erbe, pHash-Face-Dedupe §8.3) wie jeder andere Edit-Import — nicht doppelt implementieren, P8-Pfad nutzen.
- Frontend: „Aus ComfyUI-Output importieren" (vom Quell-Asset oder vom Run-Status aus erreichbar) → Ergebnis-Liste → Auswahl → Import → erscheint als Edit-Version.

## Checkliste

- [ ] Route `GET /api/comfyui/results` (history-Pfad + output_dir-Pfad, Vorschau)
- [ ] `type = comfyui` im Versions-Enum/-Schema ergänzen (P8-kompatibel)
- [ ] Import-Verdrahtung auf `POST /api/assets/{id}/versions/import` (Datei aus `/view`/`output_dir` → P8-Import)
- [ ] Frontend: Import-Auswahl-UI (Ergebnis-Liste, Vorschau, Auswahl → Import)
- [ ] Tests: results aus gemocktem `/history`; results aus `output_dir`; Import erzeugt Version mit Lineage + korrektem `type`
- [ ] Doc-Update: README-Kontrakt, `type = comfyui` im Versions-Doc, Smoke-Checkliste

## Report-Back
