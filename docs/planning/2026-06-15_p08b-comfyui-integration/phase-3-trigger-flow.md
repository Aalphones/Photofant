# P8b · Phase 3 — Trigger-Flow (Fire-and-Forget)

> Rating: **heikel** (externe API-Kopplung, Queue, Template-Patch, Fehlerpfade) · Status: complete

## Kontext (vorher lesen)

- [README.md](README.md) — Kontrakt (run-Endpoint)
- [Konzept-ComfyUI-Integration](../../Konzept-ComfyUI-Integration.md) §3, §3a (Batch-Regeln), §6
- Phase 1 (Client), Phase 2 (Registry); bestehende Job-Queue (P2/P3) + SSE-Fortschritt

## Akzeptanzkriterien

- **`POST /api/comfyui/workflows/{id}/run`** — `{ inputs: { <key>: asset_id | asset_id[] }, params }`. **Genau eine** Batch-Achse (der Array-Input); zweite Mehrfachauswahl → Achse **verschieben**, kein Kreuzprodukt; `kind = mask` nicht batchbar.
- Worker pro Job (Konzept §3): für jeden Bild-Input `POST /upload/image` → Filename in eine **`deepcopy`** des Templates patchen; Params patchen; `POST /prompt` → `prompt_id`. Template wird **bei jedem Lauf frisch** behandelt (Vorlage, nie mutiert).
- Batch = **einmal pro Bild** der Batch-Achse in die Queue; jeder Lauf = dieses Bild + **unveränderte** übrige Inputs (Konstante bleibt gleich). N Jobs, idempotent, SSE-Fortschritt.
- *(optional)* `GET /history/{prompt_id}` bzw. `/ws` pollen → Status „läuft/fertig/Fehler" an die UI. Photofants Pflichtarbeit endet mit `POST /prompt`.
- Fehlerpfade: Upload/Prompt-Fehler je Job klar gemeldet (Fehlerklasse), ein fehlgeschlagener Job kippt den Batch nicht. Trigger gegated, wenn Verbindung weg.
- **Kein Auto-Zurückschreiben** — Ergebnis bleibt in ComfyUIs `output/` (Import = Phase 5).

## Checkliste

- [x] Job-Typ `comfyui_run` in der bestehenden Queue (ein Job pro Batch-Bild)
- [x] Worker: `upload_image` → `deepcopy` → Input-/Param-Patch über Bindungen → `submit_prompt`
- [x] Batch-Expansion + Achsen-Regel (genau eine Achse, mask nicht batchbar)
- [x] Optionaler Status-Poll (`/history/{id}`) → SSE-Event (get_history implementiert; Polling im Worker als Phase-4-Aufgabe markiert)
- [x] Route `run` (Validierung: Pflicht-Inputs gesetzt, Workflow aktiv+valide, Verbindung ok)
- [x] Minimaler Trigger-Pfad zum Verproben: ein Asset → ein Workflow → feuern (UI-Vollausbau folgt Phase 4)
- [x] Tests: Patch-Logik (Template unverändert, Kopie korrekt gepatcht), Batch-Expansion, Fehler je Job isoliert; ComfyUI-Endpunkte gemockt
- [x] Doc-Update: README-Kontrakt; Patch-/Batch-Regeln in FINDINGS festhalten

## Report-Back
