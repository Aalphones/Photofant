# P2 · Phase 2 — Thumbnail-Cache

> Rating: standard · Status: pending

## Kontext (vorher lesen)

- [README.md](README.md) — Kontrakt (Thumbnail-Endpoint, Cache-Header)
- [Konzept](../../Konzept-Photofant.md) §4.1 (Cache-DB-Prinzip), §5 (thumbnails.sqlite-Schema), §16 (Performance)

## Akzeptanzkriterien

- `thumbnails.sqlite` separat von `db.sqlite`; `thumbnail`-Tabelle nach Konzept (target_kind/target_id/size/blob).
- Thumbnail-Erzeugung (256 + 512, JPEG/WebP) als Queue-Job, automatisch nach Import; fehlende Thumbs werden on-demand nachgeneriert.
- `GET /api/assets/{id}/thumbnail?size=` liefert mit `ETag` (content_hash-basiert) + `Cache-Control`; 304-Handling.
- Kompletter Cache löschbar und regenerierbar, ohne dass `db.sqlite` angefasst wird (Vorgriff auf P3-Rebuild).

## Checkliste

- [ ] Zweite SQLite-Engine/Session für die Cache-DB (eigene Datei, kein Alembic nötig — Schema wird bei Fehlen erzeugt, da Wegwerf-Cache)
- [ ] Thumbnail-Generator (Pillow, EXIF-Orientierung beachten) als Queue-Job, Batch nach Import
- [ ] Endpoint mit ETag/304 + sinnvoller Content-Type
- [ ] On-Demand-Fallback: Thumb fehlt → synchron klein erzeugen oder Platzhalter + Job
- [ ] Doc-Update: docs/models.md um Cache-DB ergänzen

## Report-Back
