# P5 · Phase 2 — WD14-Tagging

> Rating: standard · Status: complete

## Kontext (vorher lesen)

- [README.md](README.md) — Kontrakt (Dto-Erweiterung)
- [Konzept](../../Konzept-Photofant.md) §5 (tag/asset_tag), §6.2 (Matrix)
- Phase 1 (Interfaces)

## Akzeptanzkriterien

- Migration: `tag`, `asset_tag` nach Konzept §5.
- WD14-Tagger (swinv2-v3, ONNX + CSV-Labelmap) liefert Tags über Konfidenz-Schwelle (Default ~0.35, in `app_config`); Rating-Tags der Labelmap werden verworfen (keine NSFW-Klassifizierung — Nicht-Ziel).
- Tagging-Job im Import-Fluss (Ledger `tags_done`); Tags als `kind = auto`, Dedupe über `tag.name`.
- Detail-Panel zeigt Tag-Chips (auto-Styling nach Prototyp); manuelle Bearbeitung kommt in P6.

## Checkliste

- [x] Migration + Tag-Upsert-Logik (case-normalisiert, underscores → Anzeige mit Leerzeichen wie Booru-üblich)
- [x] WD14-Implementierung des `Tagger`-Interface (CSV-Parsing, Schwelle, Kategorie-Filter)
- [x] Job + Ledger-Integration
- [x] Dto/Endpoint-Erweiterung + Frontend-Tags-Sektion im Detail-Panel
- [x] Doc-Update: docs/models.md (tag-Tabellen)

## Report-Back

`backend/alembic/versions/0005_tag_tables.py` — Migration: `tag` (id, name UNIQUE) + `asset_tag` (id, asset_id, tag_id, kind, score).
`backend/photofant/db/models.py` — `Tag` + `AssetTag` SQLAlchemy-Modelle.
`backend/photofant/inference/adapters/wd14.py` — `WD14Tagger` + `resolve_wd14_tagger()`; CSV-Labels per `lru_cache`; ONNX-Session via `session_manager`; Rating-Tags (category=9) gefiltert.
`backend/photofant/jobs/tagging_job.py` — `run_tagging_job` (blocking in Thread), `enqueue_tagging`; Schwelle aus `app_config`; Ledger `tags_done` gesetzt.
`backend/photofant/jobs/import_job.py` — `_enqueue_tagging_batch` nach jeder Import-/Scan-Runde.
`backend/photofant/api/assets.py` — `TagDto`, `_load_asset_tags()`, `AssetDetailDto` um `tags` + `tagger` erweitert.
`frontend/src/app/models/` — `TagDto` + `AssetDetailDto.tags/tagger`.
`frontend/.../lightbox.*` — `detail`-Signal (toSignal auf getAsset), `displayTags` (computed, underscores→spaces), Tag-Chips-Sektion im Panel.
