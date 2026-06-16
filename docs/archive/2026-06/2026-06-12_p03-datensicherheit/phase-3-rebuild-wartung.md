# P3 · Phase 3 — Rebuild & Wartungs-View

> Rating: standard · Status: complete

## Kontext (vorher lesen)

- [README.md](README.md) — Kontrakt
- [Konzept](../../Konzept-Photofant.md) §13.3
- [docs/design/README.md](../../design/README.md) — Einstellungen-Sektionen; `docs/design/js/maintenance.jsx`, `docs/design/maintenance.css`

## Akzeptanzkriterien

- Thumbnail-Rebuild regeneriert die komplette Cache-DB aus den Bilddateien (Queue, Fortschritt); jederzeit abbrechbar ohne Schaden.
- Wartungs-View nach Prototyp fasst zusammen: Backup (Phase 1), Reconcile (Phase 2), Rebuild — mit Status, letzter Ausführung, laufenden Jobs.
- Rebuild-Endpoint ist um weitere Targets erweiterbar (P7 hängt `faces` an).

## Checkliste

- [x] Rebuild-Job (Cache-DB leeren/neu aufbauen, Batch über alle Instanzen)
- [x] `maintenance`-Slice (Status, Report, letzte Läufe)
- [x] Wartungs-View (Gruppen nach Prototyp-Settings-Pattern: Row + Aktion + Sub-Text)
- [x] Doc-Update: routes.md; AGENTS.md Critical Rules geprüft — nichts Neues nötig (Rebuild fällt unter Regel 3/5: schwere Arbeit über Queue, Cache jederzeit rebuildbar)

## Report-Back

**Backend**
- `JobKind.REBUILD` ergänzt; `rebuild_job.py` (target-dispatched, P7 hängt `faces` an): leert `thumbnails.sqlite` und regeneriert alle aktiven Instanzen über den geteilten `generate_thumbnails`-Helper (aus `thumbnail_job.py` extrahiert).
- `POST /api/maintenance/rebuild { target: 'thumbnails' }` + `GET /api/maintenance/status` (db_size, thumbnail_count, cache_size). `count_thumbnail_targets()` in `db/cache.py`.

**Frontend**
- Store: `rebuildingTarget` + `status` im State; Actions/Effects für Rebuild-Trigger, Status-Load und Job-Ende (Rebuild-done → Status neu laden). `'rebuild'` in `JOB_KINDS`.
- Neue `/wartung`-Route + `Wartung`-View: Status-Leiste (4 Stats) + FS↔DB-Scan (aus Einstellungen übernommen) + Thumbnail-Rebuild. Nav-Eintrag „Wartung" (`wrench`).
- `Einstellungen` auf reines Backup reduziert.

**Abweichungen / Notizen**
- „Abbrechbar ohne Schaden" ist by-design erfüllt (Cache-only, Originale unangetastet, fehlende Thumbnails regenerieren lazy via `GET /assets/{id}/thumbnail`) — **kein** expliziter Cancel-Button (Prototyp hat auch keinen).
- Face-Rebuild + Face-Status-Stat als „ab P7" markiert (kein Backend).
- 🟡 Wartung-Komponenten-CSS überschreitet das 4-kB-Budget um 722 B (Warnung, Präzedenzfall `import-dialog.scss`).
