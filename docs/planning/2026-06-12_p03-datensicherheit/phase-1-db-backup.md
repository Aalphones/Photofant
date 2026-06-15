# P3 · Phase 1 — DB-Backup

> Rating: mechanisch · Status: pending

## Kontext (vorher lesen)

- [README.md](README.md) — Kontrakt
- [Konzept](../../Konzept-Photofant.md) §13.1

## Akzeptanzkriterien

- Snapshot über die SQLite-Online-Backup-API (konsistent auch bei laufender App), Zeitstempel im Dateinamen, Ziel `.photofant/backups/` oder wählbarer Ordner.
- Läuft als Queue-Job mit Fortschritt; alte Backups werden gelistet (Name, Größe, Datum).

## Checkliste

- [ ] Backup-Job (sqlite3 `backup()`-API, nie File-Copy einer offenen DB)
- [ ] Endpoint + Listing (`GET /api/maintenance/backups`)
- [ ] UI-Sektion (Backup-Button, Ziel-Anzeige, Liste) in Einstellungen → Backup & Wartung
- [ ] Doc-Update: routes.md

## Report-Back
