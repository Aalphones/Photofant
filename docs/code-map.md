# Code-Map — Photofant

> **Zweck:** Feature → Dateien als vertikale Slices über Frontend + Backend. Macht aus „wo ist Feature X" N Greps → einen Read. **Bewusst grob** (Ordner-/Modul-Ebene, keine Zeilennummern), damit sie Refactorings überlebt. Pflege: code-reference doc — bei Strukturänderung (neuer Feature-Ordner/Modul, verschobene Dateien) nachziehen.

## Navigations-Trick: die Namen laufen parallel

Frontend-Feature, Store-Slice, Service, Backend-API und Job heißen fast überall gleich. Wer ein Feature sucht, rät den Namen statt zu grep'en:

```
features/<x>/  ·  store/<x>/  ·  services/<x>.service.ts  ·  api/<x>.py  ·  jobs/<x>_job.py
```

Pfade unten relativ zu `frontend/src/app/` bzw. `backend/photofant/`.

## Kern: Galerie, Suche, Klassifizierung

| Feature | Frontend | Backend |
|---|---|---|
| **Galerie & Lightbox** | `features/galerie/` (galerie, grid, cell, lightbox[+zoom-stage], filter-rail, sub-toolbar — kein `edits`-Tab mehr seit P21) · `store/gallery/` (Entity-Key: `String(id)` für Assets, `` `v${version_id}` `` für Version-Pseudo-Einträge — P21 ADR-012), `store/filters/` · `ui/import-dialog/`, `ui/bulk-bar/` · `models/asset.model.ts` | `api/assets.py` (Stapel-Query: mischt `asset`- und `version`-Zeilen zu flachen Einzeleinträgen mit `stack_size`/`stack_group_id`, P21 ADR-012) · `jobs/import_job.py`, `jobs/thumbnail_job.py` · `media/thumbnails.py`, `media/moves.py`, `media/meta.py` |
| **Suche** (Tag/Caption/semantisch) | `ui/search-box/` · `store/search/` | `api/search.py` · `db/vector_index.py` · `jobs/embedding_job.py` · `inference/adapters/clip.py` |
| **Tags** | `features/einstellungen/tags/` · `store/tags/` · `services/tag.service.ts` | `api/tags.py` · `jobs/tagging_job.py` · `inference/adapters/wd14.py` |
| **Captions & Presets** | `ui/caption-preset-form/`, `ui/preset-dialog/` · `store/presets/` · `services/caption-preset.service.ts` · `models/caption-preset.model.ts` | `api/caption_presets.py` · `jobs/caption_job.py` · `inference/caption_config.py` · `inference/adapters/{florence2,joycaption,qwen_vl}.py` |
| **Klassifizierung & Heuristik** | `services/classify.service.ts` | `api/classify.py` · `jobs/heuristics_job.py` |
| **Alben & Smart-Alben** | `features/alben/` (alben, album-settings) · `store/collections/` · `services/collection.service.ts` · `models/collection.model.ts` | `api/collections.py` · `collections/engine.py` · `jobs/collections_job.py` |

## Personen, Faces, Review

| Feature | Frontend | Backend |
|---|---|---|
| **Personen & Faces** | `features/personen/` (personen, person-card, merge/split/dupe-check-dialog) · `features/galerie/face-cell/`, `face-grid/` · `store/persons/` · `services/person.service.ts` · `models/person.model.ts` | `api/faces.py`, `api/persons.py` · `jobs/face_job.py`, `jobs/clustering_job.py` · `clustering/engine.py` · `inference/adapters/buffalo_l.py` · `db/face_vector_index.py` · `media/person_folders.py` |
| **Review-Queue** (Faces + Dupes) | `features/review/` (review, review-faces, review-dupes[+dupe-compare, dupe-pair-row]) · `store/review/` · `services/review.service.ts` · `models/review.model.ts` | `api/review.py`, `api/review_queue.py`, `api/duplicates.py` · `jobs/dupe_scan_job.py` · `media/phash.py` |

## Editor & Generativ

| Feature | Frontend | Backend |
|---|---|---|
| **Editor** (CPU: Crop/Rotate/rembg) | `features/editor/` (editor, basis-panel, crop-overlay, mask-overlay, step-bar, save-modal) · `store/editor/` · `services/edit-session.service.ts` · `models/edit-session.model.ts` · `ui/bulk-edit-dialog/` | `api/edit_sessions.py` · `jobs/bulk_edit_job.py` · `media/ops.py` |
| **Generativ** (Upscale/Edit/Inpaint via ComfyUI) | `features/editor/` (flux2-panel = Edit, inpaint-panel, upscale-panel, resolution-field) · `store/editor/` (runGenerative) · `features/galerie/run-leiste/` (Prompt/Resolution) · Bulk-Upscale: `ui/bulk-bar/` + Galerie · Einzel-Upscale: `galerie/lightbox/`. Default-Aktionen (Edit/Inpaint/Upscale) über `services/comfyui.service.ts` (`runDefaultWorkflow` → Auto-Import); Run-Leiste über `runWorkflow` (Fire-and-forget bleibt) | `api/comfyui.py` · `jobs/comfyui_run_job.py` · `inference/generative_engine.py` (nur heavy_captioners) |
| **ComfyUI-Integration** | `features/galerie/run-leiste/` · `features/einstellungen/comfyui/` · `ui/comfyui-import-dialog/` · `store/comfyui/`, `store/prompt-templates/` · `services/comfyui.service.ts`, `prompt-template.service.ts` · `models/comfyui-workflow.model.ts`, `prompt-template.model.ts` | `api/comfyui.py`, `api/prompt_templates.py` · `jobs/comfyui_run_job.py` · `comfyui/` (client, introspect, validator) · Workflow-Discovery: `.photofant/workflows/*.json` (Dateiname = key, kein Upload/DB) — 3 Default-Zuordnungen (Upscale/Edit/Inpaint) in `settings.json`; Default-Run importiert kuratierte Ergebnisse automatisch, generischer Run bleibt Fire-and-forget |

## Verwaltung

| Feature | Frontend | Backend |
|---|---|---|
| **Modell-Management** | `features/modelle/` (modelle, bind-dialog, download-dialog, model-card, model-drawer) · `store/models/` · `services/model.service.ts` · `models/model.model.ts` | `api/models.py` · `models/loader.py`, `models/validation.py`, `models/vram.py` · `jobs/download_job.py` · `inference/session_manager.py` |
| **Wartung & Datensicherheit** | `features/wartung/` · `features/review/review-reconcile/` (Reconcile-Report-UI, Shell + generische `rr-section`-Child) · `features/einstellungen/backup-wartung/` · `store/maintenance/` · `services/maintenance.service.ts` · `models/maintenance.model.ts` | `api/maintenance.py` · `maintenance/` (reconcile, repair, store) · `jobs/{rebuild,reconcile,backup}_job.py` |
| **Papierkorb & Favoriten** | `features/papierkorb/`, `features/favoriten/` · `store/trash/` | `api/trash.py` · `media/moves.py` (Favorit = physischer Move) |
| **Einstellungen** | `features/einstellungen/` (Shell + darstellung, bibliothek, verarbeitung, bearbeitung, info, tastaturkuerzel, tags, comfyui, backup-wartung) · `services/settings.service.ts` · `models/config.model.ts` | `api/config.py` · `settings.py`, `config.py` |
| **Trainingssets & Export** | `features/trainingssets/` | (nutzt `api/assets.py` + `api/collections.py`; eigener Backend-Pfad noch dünn) |

## Querschnitt (überall benutzt)

| Bereich | Frontend | Backend |
|---|---|---|
| **App-Shell & Auth** | `app.component.ts`, `app.config.ts`, `app.routes.ts` · `shell/` (shell, nav-rail, top-bar) · `guards/auth.guard.ts` · `features/unlock/` · `services/auth.service.ts` | `main.py` · `api/auth.py`, `api/health.py`, `api/info.py` |
| **Jobs / Queue** (alles Langsame) | `ui/job-dock/`, `ui/job-pill/`, `ui/rerun-dialog/` · `store/jobs/` · `services/jobs.service.ts` · `models/job.model.ts` | `api/jobs.py` · `jobs/queue.py` · `jobs/rerun_job.py` |
| **DB & Persistenz** | — | `db/` (engine, session, models, cache, vector_index, face_vector_index) · `alembic/versions/` (Migrationen) |
| **Inferenz-Infra** | `ui/gated-feature/` (Feature-Gating) | `inference/` (interfaces, preprocessing, session_manager) · `models/loader.py` |
| **UI-Bausteine** | `ui/icon/`, `ui/shortcut-legend/` · `services/shortcut.service.ts` | — |

## Wo was wohnt (Faustregeln)

- **Eine HTTP-Route suchen?** → `backend/photofant/api/<feature>.py`, gespiegelt in `docs/routes.md`.
- **Ein DB-Feld suchen?** → `backend/photofant/db/models.py`, gespiegelt in `docs/models.md`.
- **„Langsam, aber blockiert die UI nicht"?** → es läuft als Job: `backend/photofant/jobs/<x>_job.py`, orchestriert von `jobs/queue.py`. Die Queue hat drei Spuren: parallel (Downloads, fire-and-forget) · Main-Worker FIFO (user-getriggert: Import, Export, ComfyUI-Run, Scan, Backup …) · Background-Worker mit Prioritäts-Queue (Hintergrund-Inferenz: Face vor Tagging/Embedding vor Captioning — `_BACKGROUND_PRIORITY` in `queue.py`). So warten schnelle user-Jobs nie hinter einem langsamen Caption-Lauf.
- **ML-Modell-Adapter?** → `backend/photofant/inference/adapters/`.
- **NgRx-State zu einem Feature?** → `frontend/src/app/store/<feature>/`.
