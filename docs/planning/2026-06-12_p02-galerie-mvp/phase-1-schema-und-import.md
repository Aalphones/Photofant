# P2 · Phase 1 — Schema & Import-Backend

> Rating: standard · Status: pending

## Kontext (vorher lesen)

- [README.md](README.md) — Kontrakt (Dto, Endpoints, Stage-1-Vereinfachung)
- [Konzept](../../Konzept-Photofant.md) §4 (Datenhaltung), §5 (Schema: asset, asset_instance, person, processing_ledger), §6.1 Schritte 1–3
- [docs/conventions/python.md](../../conventions/python.md) — SQLite-Datetime-Strategie, Move+DB-Regel

## Akzeptanzkriterien

- Migration legt `asset`, `asset_instance`, `person` (mit `_unknown`-Zeile), `processing_ledger` an — Spalten vollständig nach Konzept §5, auch die erst später befüllten (caption, embedding, …), damit spätere Pläne nur Daten, nicht Schema nachziehen.
- Import (Single/Bulk/Scan) als Queue-Job: SHA-256, Ledger-Check (Dedupe), EXIF/PNG-Chunks lesen (`generation_meta`, `created_at`, Dimensionen, Format, `source`-Ableitung original/sdxl/flux), Kopie nach `Data/_unknown/photos/`, DB-Einträge.
- `GET /api/assets` mit Pagination/Sortierung (indizierte Queries), `GET /api/assets/{id}`.

## Checkliste

- [ ] Alembic-Migration: Tabellen aus Konzept §5 (asset, asset_instance, person, processing_ledger; tag/collection-Tabellen erst in P5/P6)
- [ ] `Data/`-Root konfigurierbar (`app_config`), Ordnerstruktur-Anlage (`_unknown/photos|favourites|faces|edits`, `.photofant/`)
- [ ] Hash- + Metadaten-Modul (Pillow für EXIF, PNG-Text-Chunks für ComfyUI/A1111-Workflows → `generation_meta` JSON, `source`-Heuristik)
- [ ] Import-Job (Single/Bulk) + Scan-Job (Dateien ohne DB-Eintrag finden) über die Queue, Fortschritt pro Datei
- [ ] `GET /api/assets` (Pagination, Sort date/size, favourite-Filter vorbereitet) + Detail-Endpoint
- [ ] Indizes: `asset.content_hash` (unique), `asset.created_at`, `asset_instance.deleted_at`
- [ ] Doc-Update: docs/models.md anlegen (Tabellen-Referenz)

## Report-Back
