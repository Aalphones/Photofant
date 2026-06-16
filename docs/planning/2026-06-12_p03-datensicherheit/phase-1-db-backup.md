# P3 · Phase 1 — DB-Backup

> Rating: mechanisch · Status: complete

## Kontext (vorher lesen)

- [README.md](README.md) — Kontrakt
- [Konzept](../../Konzept-Photofant.md) §13.1

## Akzeptanzkriterien

- Snapshot über die SQLite-Online-Backup-API (konsistent auch bei laufender App), Zeitstempel im Dateinamen, Ziel `.photofant/backups/` oder wählbarer Ordner.
- Läuft als Queue-Job mit Fortschritt; alte Backups werden gelistet (Name, Größe, Datum).

## Checkliste

- [x] Backup-Job (sqlite3 `backup()`-API, nie File-Copy einer offenen DB)
- [x] Endpoint + Listing (`GET /api/maintenance/backups`)
- [x] UI-Sektion (Backup-Button, Ziel-Anzeige, Liste) in Einstellungen → Backup & Wartung
- [x] Doc-Update: routes.md

## Report-Back
