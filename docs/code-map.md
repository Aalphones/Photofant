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
| **Galerie & Lightbox** | `features/galerie/` (galerie, grid[+`row-layout.ts` — pure Row-Breaking-Engine; `grid.ts` hostet `@tanstack/angular-virtual` row-level, flache `assets`-Liste statt Monatsgruppen, `#loadSentinel`/IntersectionObserver entfernt — P20], cell, face-grid[eigener Scroll-Container], lightbox[+zoom-stage, +`related-rail/` — generische „Ähnliche Bilder"-Kartenliste `{assetId, score, reasons}`, P36, ersetzt das alte Similar-Overlay; von P26 (Recommendation Engine) später mit befüllten `reasons` wiederverwendet], filter-rail, sub-toolbar — kein `edits`-Tab mehr seit P21) · `store/gallery/` (Entity-Key: `String(id)` für Assets, `` `v${version_id}` `` für Version-Pseudo-Einträge — P21 ADR-012), `store/filters/` · `ui/import-dialog/`, `ui/bulk-bar/` · `models/asset.model.ts`, `models/related-rail.model.ts` | `api/assets.py` (Stapel-Query: mischt `asset`- und `version`-Zeilen zu flachen Einzeleinträgen mit `stack_size`/`stack_group_id`, P21 ADR-012) · `jobs/import_job.py`, `jobs/thumbnail_job.py` · `media/thumbnails.py`, `media/moves.py`, `media/meta.py` · `api/review.py` (`GET /assets/{id}/similar` — nur noch MCP-Aufrufer, kein Frontend-Caller mehr seit P36 Phase 3) |
| **Suche** (Freitext exakt/Prefix, Tag, Caption, semantisch, Reverse-Image) | `ui/search-box/` (Drop-Zone + Bild-Upload → Reverse; expliziter Semantik-Umschalter mit Tooltip, P36 Phase 4 — Quelle der Wahrheit ist `store/search`s `mode`, lokal nur `pendingSemanticToggle` für „getoggelt, noch kein Text") · `store/search/` · `store/filters/` (`reverseSearch` = exklusiver Reverse-Filter-Modus, P36) · `store/gallery/gallery.effects.ts` (Ladefehler → deutsche Meldung via `extractApiErrorMessage`, angezeigt in `features/galerie/galerie.ts` als Toast, P36 Phase 4) · `services/search.service.ts` (`by-image`, `semanticByAsset` — Lightbox-Rail + „mehr"-Sprung, P36) · `services/api-error.util.ts` (`extractApiErrorMessage` — geteilter Backend-Fehlertext-Parser, P36 Phase 4) · `models/search.model.ts` | `api/assets.py` (`list_assets`, alle `q_mode`-Zweige; `q_mode=text` = Tag-/Personen-Name ILIKE + Caption via FTS5, Fuzzy-Toleranz entfernt, ADR-015-Nachtrag; `q_mode=semantic` bleibt bewusst der einzige Frontend-Pfad der Text-Semantiksuche, P36 Phase 4 — volle Paginierung/Facetten statt Doppel-Roundtrip über `/api/search/semantic`; `similar_ids`-Param sortiert nach vorgegebener Reihenfolge, P36) · `db/text_index.py` (FTS5-Caption-Index `asset_caption_fts`) · `api/search.py` (`POST /api/search/semantic` — nur `like_asset_id`-Zweig hat einen Frontend-Aufrufer (Lightbox-Rail + „mehr"), P36; `query`-Zweig bleibt bewusst totes Backend-Duplikat, siehe `docs/routes.md`; `POST /api/search/by-image` — Upload-Embed für Reverse Image Search, P36) · `db/vector_index.py` · `jobs/embedding_job.py` · `inference/image_embedder.py` (Capability-Resolver `resolve_image_embedder`, ADR-022) · `inference/adapters/clip.py` · `inference/adapters/siglip.py` |
| **Tags** | `features/einstellungen/tags/` · `store/tags/` · `services/tag.service.ts` | `api/tags.py` · `jobs/tagging_job.py` · `inference/adapters/wd14.py` |
| **Captions & Presets** | `ui/caption-preset-form/`, `ui/preset-dialog/` · `store/presets/` · `services/caption-preset.service.ts` · `models/caption-preset.model.ts` | `api/caption_presets.py` · `jobs/caption_job.py` · `inference/caption_config.py` · `inference/adapters/{florence2,joycaption,qwen_vl}.py` |
| **Klassifizierung & Heuristik** (P18) | `services/classify.service.ts` · `features/einstellungen/klassifizierung/` (Shell + Child `kategorie-editor/` — Kategorien/Labels-CRUD, Modus-Umschalter, Seed-Katalog editierbar) · `store/classification/` (Entity-Store der Kategorien, `classification.effects.ts` ruft `services/classification.service.ts`) · `models/classification.model.ts` (`ClassificationCategory`, `ClassificationLabel`, `AssetClassification`) · Lightbox-Sektion + Galerie-Filter-Rail-Gruppe je Kategorie: `features/galerie/lightbox/`, `features/galerie/filter-rail/` | `api/classify.py` (Rerun-Step `categories`) · `api/classification.py` (CRUD Kategorien/Labels, explizites Cascade-Delete — `PRAGMA foreign_keys` projektweit aus) · `api/assets.py` (`classification`-Filter OR/AND, Facet `classifications`, `AssetDetailDto.classifications`, Label-Treffer im `q_mode=text`) · `jobs/heuristics_job.py` · `classification/engine.py` (CLIP+WD14-Fusion, kein Modell-Neulauf), `classification/scoring.py`, `classification/seed.py` (Konzept-Seed-Katalog) · `jobs/classification_job.py` (ein Asset, persistiert + setzt `ProcessingLedger.classified`), `jobs/classification_pipeline.py` (wartet auf Tagging+Embedding, enqueued dann `classification_job`) |
| **Alben & Smart-Alben** | `features/alben/` (alben, album-settings) · `store/collections/` · `services/collection.service.ts` · `models/collection.model.ts` | `api/collections.py` · `collections/engine.py` · `jobs/collections_job.py` |

## Personen, Faces, Review

| Feature | Frontend | Backend |
|---|---|---|
| **Personen & Faces** | `features/personen/` (personen, person-card, merge/split/dupe-check/delete-person-dialog, alphabet-rail, group-color.util.ts) · `features/galerie/face-cell/`, `face-grid/` · `store/persons/` · `services/person.service.ts` · `models/person.model.ts` | `api/faces.py`, `api/persons.py`, `api/assets.py` (`PATCH /assets/{id}/assign-person`, P30 — Person ohne Face zuordnen) · `jobs/face_job.py`, `jobs/clustering_job.py` · `clustering/engine.py` · `inference/adapters/buffalo_l.py` · `db/face_vector_index.py` · `media/person_folders.py` (inkl. `delete_person()`, `_resolve_person_smart_triggers()`) |
| **Review-Queue** (Faces + Dupes) | `features/review/` (review, review-faces, review-dupes[+dupe-compare, dupe-pair-row]) · `store/review/` · `services/review.service.ts` · `models/review.model.ts` | `api/review.py`, `api/review_queue.py`, `api/duplicates.py` · `jobs/dupe_scan_job.py` (CLIP-only, ADR-018) |

## Editor & Generativ

| Feature | Frontend | Backend |
|---|---|---|
| **Editor** (CPU: Crop/Rotate/rembg) | `features/editor/` (editor, basis-panel, crop-overlay, mask-overlay, step-bar, save-modal) · `store/editor/` · `services/edit-session.service.ts` · `models/edit-session.model.ts` · `ui/bulk-edit-dialog/` | `api/edit_sessions.py` · `jobs/bulk_edit_job.py` · `media/ops.py` · `media/orientation_overwrite.py` (reine Orientierungs-Sessions rotate/mirror überschreiben Quelle statt neue Version, P-editor-basis-fixes Phase 3) |
| **Generativ** (Upscale/Edit/Inpaint via ComfyUI) | `features/editor/` (flux2-panel = Edit, inpaint-panel, upscale-panel, resolution-field) · `store/editor/` (runGenerative) · `features/galerie/run-leiste/` (Prompt/Resolution) · Bulk-Upscale: `ui/bulk-bar/` + Galerie · Einzel-Upscale: `galerie/lightbox/`. Default-Aktionen (Edit/Inpaint/Upscale) über `services/comfyui.service.ts` (`runDefaultWorkflow` → Auto-Import); Run-Leiste über `runWorkflow` (Fire-and-forget bleibt) | `api/comfyui.py` · `jobs/comfyui_run_job.py` · `inference/generative_engine.py` (nur heavy_captioners) |
| **ComfyUI-Integration** | `features/galerie/run-leiste/` · `features/einstellungen/comfyui/` · `ui/comfyui-import-dialog/` · `store/comfyui/`, `store/prompt-templates/` · `services/comfyui.service.ts`, `prompt-template.service.ts` · `services/run-draft.service.ts` (Run-Leisten-Entwurf tab-übergreifend: Slot-Belegungen/Workflow/Toggles leben hier statt in `galerie.ts`, Live-Sync über `BroadcastChannel` + `localStorage`; „scharfer" Slot bleibt lokal in `galerie.ts`) · `models/comfyui-workflow.model.ts`, `prompt-template.model.ts` | `api/comfyui.py`, `api/prompt_templates.py` · `jobs/comfyui_run_job.py` · `comfyui/` (client, introspect, validator) · Workflow-Discovery: `.photofant/workflows/*.json` (Dateiname = key, kein Upload/DB) — 3 Default-Zuordnungen (Upscale/Edit/Inpaint) in `settings.json`; Default-Run importiert kuratierte Ergebnisse automatisch, generischer Run bleibt Fire-and-forget |

## Verwaltung

| Feature | Frontend | Backend |
|---|---|---|
| **Modell-Management** | `features/modelle/` (modelle, bind-dialog, download-dialog, model-card, model-drawer) · `store/models/` · `services/model.service.ts` · `models/model.model.ts` | `api/models.py` · `models/loader.py`, `models/validation.py`, `models/vram.py` · `jobs/download_job.py` · `inference/session_manager.py` |
| **Wartung & Datensicherheit** | `features/wartung/` (FS↔DB-Reconcile, Thumbnail-Rebuilds, Bild-Re-Embed, Personen-Clustering, Backup — eine Seite, kein Einstellungen-Tab) · `features/review/review-reconcile/` (Reconcile-Report-UI, Shell + generische `rr-section`-Child) · `store/maintenance/` · `services/maintenance.service.ts` · `services/classify.service.ts` (Re-Embed nutzt `POST /api/classify/rerun` mit `asset_ids:"all"`) · `models/maintenance.model.ts` | `api/maintenance.py` · `api/classify.py` · `maintenance/` (reconcile, repair, store) · `jobs/{rebuild,reconcile,backup,rerun}_job.py` |
| **Papierkorb & Favoriten** | `features/papierkorb/`, `features/favoriten/` · `store/trash/` | `api/trash.py` · `media/moves.py` (Favorit = physischer Move) |
| **Einstellungen** | `features/einstellungen/` (Shell + darstellung, bibliothek, verarbeitung, bearbeitung, info, tastaturkuerzel, tags, klassifizierung, comfyui, mcp) · `services/settings.service.ts` · `models/config.model.ts` | `api/config.py` · `settings.py`, `config.py` |
| **MCP-Schnittstelle** (Agent-Steuerung, ADR-019) | `features/einstellungen/mcp/` · `store/mcp/` · `services/mcp.service.ts` (liest/schreibt den `mcp`-Block über das generische `/api/config`) · `models/config.model.ts` (`McpConfig`) | `mcp/` (`server.py` = FastMCP-Instanz + `/mcp`-Mount + Flag-Guard/Loopback-Middleware, `adapter.py` = `run_endpoint()` DB-Session-Brücke zu `api/*.py`, `gate.py` = Confirmation-Gate, `tools/` = ein Modul je Phase) · Mount in `main.py` (`mount_mcp`, Session-Manager im `_lifespan`) · `settings.py` (`mcp`-Block) |
| **Trainingssets & Export** | `features/trainingssets/` (trainingssets, training-set-item, training-set-settings, training-set-stats, training-set-captions, training-set-dupes, training-set-export) · `ui/export-dialog/` (Galerie + Favoriten, gemeinsam) · `store/collections/` · `services/collection.service.ts`, `export.service.ts` | `api/collections.py` (`/items`, `/stats`, `/export`, `/captions`, `/duplicates`) · `api/export.py` (Favoriten-Exporte) · `jobs/export_job.py` (Sidecar-Writer, Train/Val-Split) · `collections/stats.py` (AR-Buckets, Near-Dupe-Quote) |

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
- **„Langsam, aber blockiert die UI nicht"?** → es läuft als Job: `backend/photofant/jobs/<x>_job.py`, orchestriert von `jobs/queue.py`. Die Queue hat mehrere Spuren: parallel (Downloads, fire-and-forget) · Main-Worker FIFO (user-getriggert: Import, Export, ComfyUI-Run, Scan, Backup …) · Background-Worker mit Prioritäts-Queue (Hintergrund-Inferenz: Face vor Embedding/Heuristics/Dupe-Scan — `_BACKGROUND_PRIORITY` in `queue.py`) · dedizierte Tagging- und Captioning-Worker, je in konfigurierbarer Anzahl (Settings `tagging_workers`/`captioning_workers`, Default 1) statt fix einem Worker, damit sie auf der GPU überlappen können ohne sich eine ONNX-Session zu teilen. So warten schnelle user-Jobs nie hinter einem langsamen Caption-Lauf.
- **ML-Modell-Adapter?** → `backend/photofant/inference/adapters/`.
- **NgRx-State zu einem Feature?** → `frontend/src/app/store/<feature>/`.
