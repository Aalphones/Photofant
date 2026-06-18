# Einstellungen fehlende Sektionen · Phase 1 — Verarbeitung

> Rating: **standard** · Status: pending

## Kontext (vorher lesen)

- [README.md](README.md) — Kontrakt, Config-Keys, Persistenz-Entscheidung
- `backend/photofant/jobs/import_job.py` — `_enqueue_tagging_batch`, `_enqueue_caption_batch`, `_enqueue_embedding_batch` (aktuell: immer enqueued, kein Toggle)
- `backend/photofant/jobs/tagging_job.py` — `_get_threshold()` liest `tagging_threshold` aus `app_config` (bereits vorhanden → nur in UI surfacen)
- `backend/photofant/jobs/heuristics_job.py` — `_REFERENCE_SHARPNESS = 200.0` hardcodiert (→ konfigurierbar machen)
- `backend/photofant/api/config.py` — `_read_config()`, `patch_config()`

## Was in Scope ist (bereits implementiert, nur noch nicht konfigurierbar)

| Einstellung | Mockup-Label | Status heute | Maßnahme |
|---|---|---|---|
| `auto_tag` | Auto-Tagging (WD14) | immer an, kein Toggle | Toggle + `_enqueue_tagging_batch` guard |
| `auto_caption` | Auto-Caption (Florence-2) | immer an, kein Toggle | Toggle + `_enqueue_caption_batch` guard |
| `auto_embed` | CLIP-Embedding | immer an, kein Toggle | Toggle + `_enqueue_embedding_batch` guard |
| `tagging_threshold` | Erkennungs-Schwellwert (WD14) | `app_config`-Lesezugriff vorhanden | nur UI, kein Backend-Änderungsbedarf |
| `blur_threshold` | Laplacian-Varianz (Mindestschärfe) | hardcoded `200.0` in heuristics_job | in `app_config` verlagern |

## Was explizit NICHT in Scope ist (noch nicht implementiert)

- Face-Threshold, Face-Padding, Review-Queue → P7
- pHash-Schwellwert, Embedding-Duplikat → noch nicht implementiert
- rembg → noch nicht implementiert
- Import-Parallelität → erfordert Job-Queue-Rework, eigene Entscheidung
- Papierkorb-Automatik (`trash_auto_days`) → erfordert Scheduled-Task, ausgeklammert

## Akzeptanzkriterien

- `GET /api/config` liefert `auto_tag`, `auto_caption`, `auto_embed` (Defaults alle `"true"`), `blur_threshold` (Default `"200.0"`).
- Import-Job liest alle vier Toggle-Flags und enqueued selektiv.
- `blur_threshold` aus `app_config` statt hartkodiert in `heuristics_job.py`.
- Frontend-Sektion "Verarbeitung" zeigt alle fünf Einstellungen; Änderungen schreiben via `PATCH /api/config`.

## Checkliste

### Backend

- [ ] **`api/config.py` `_read_config()`**: Defaults ergänzen — `auto_tag: "true"`, `auto_caption: "true"`, `auto_embed: "true"`, `blur_threshold: "200.0"`
- [ ] **`jobs/import_job.py`**: Hilfsfunktion `_pipeline_flags() -> dict` die einmalig pro Job alle Toggle-Flags aus `app_config` liest; `_enqueue_tagging_batch`, `_enqueue_caption_batch`, `_enqueue_embedding_batch` jeweils guard `if flags["auto_tag"] != "false":`
- [ ] **`jobs/heuristics_job.py`**: `_REFERENCE_SHARPNESS` durch `_get_blur_threshold()` ersetzen (analog zu `_get_threshold()` in tagging_job.py, Key: `blur_threshold`, Fallback: `200.0`)

### Frontend

- [ ] **NgRx `models.actions.ts`**: neue Update-Action `updateProcessingConfig({ auto_tag, auto_caption, auto_embed, tagging_threshold, blur_threshold })` (oder feingranulare Einzel-Actions nach Präferenz)
- [ ] **`models.reducer.ts`**: `processingConfig: { autoTag, autoCaption, autoEmbed, taggingThreshold, blurThreshold } | null` zu `ModelsState`
- [ ] **`models.effects.ts`**: `loadConfigSuccess` extrahiert und setzt die 5 Werte; neuer Effect für Patch
- [ ] **`models.selectors.ts`**: `selectProcessingConfig` exportieren
- [ ] **`einstellungen.ts`**: neue Sektion "Verarbeitung" nach dem Muster der Darstellung-Sektion; Toggle-Switch-Komponente für die drei Booleans; Slider/Input für Schwellwerte; Werte aus Store, Änderungen via dispatch
- [ ] Doc-Update: `docs/routes.md` — neue Config-Keys dokumentieren

## Report-Back
