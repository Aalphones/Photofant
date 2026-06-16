# P3 — Datensicherheit (Querschnitt)

> Status: geparkt · Quelle: [Konzept](../../Konzept-Photofant.md) §13, §18 Querschnitt · Abhängigkeiten: P2

Die DB ist die alleinige Metadaten-Wahrheit (bewusst akzeptiertes Risiko) — dieser Plan liefert die Absicherung: Backup, FS↔DB-Abgleich, Cache-Rebuild. Früh nach P2, weil manuell eingeschobene Dateien ab sofort Drift erzeugen können.

## Overview

| Phase | Topic | Rating | Status |
|---|---|---|---|
| 1 | [DB-Backup](phase-1-db-backup.md) | mechanisch | complete |
| 2 | [FS↔DB-Reconciliation](phase-2-reconciliation.md) | heikel | complete |
| 3 | [Rebuild & Wartungs-View](phase-3-rebuild-wartung.md) | standard | pending |

## Kontrakt (Backend ↔ Frontend)

- **`POST /api/maintenance/backup`** — `{ target_dir?: string }` → Queue-Job; Snapshot (konsistente Kopie via SQLite-Backup-API) nach `.photofant/backups/` oder Zielordner, Dateiname mit Zeitstempel.
- **`POST /api/maintenance/reconcile`** — Queue-Job → Report `{ orphaned_files: [], missing_files: [], path_drift: [] }`, abrufbar über **`GET /api/maintenance/reconcile/report`**.
- **`POST /api/maintenance/reconcile/repair`** — `{ actions: [{ item, action: "index" | "mark_missing" | "trash" | "fix_path" }] }`.
- **`POST /api/maintenance/rebuild`** — `{ target: "thumbnails" }` (Face-Rebuild kommt mit P7 dazu).
- **`maintenance`-NgRx-Slice:** Job-Status + letzter Report.

## Finale Akzeptanzkriterien

1. Backup-Button erzeugt einen Snapshot, der sich (manuell zurückkopiert) als funktionierende DB erweist.
2. Manuell ins `Data/`-Verzeichnis gelegte, umbenannte und gelöschte Dateien werden vom Reconcile-Scan korrekt als verwaist/fehlend/Drift klassifiziert; jede Repair-Option wirkt wie beschriftet.
3. `thumbnails.sqlite` löschen + Rebuild → alle Thumbnails wieder da, `db.sqlite` unangetastet.
4. Alles über die UI bedienbar (Einstellungen → Backup & Wartung), kein Skript nötig; laufende Wartungs-Jobs erscheinen im Job-Dock.

## Smoke-Checkliste (User, am Plan-Ende)

- [ ] Backup erzeugen → Datei mit Zeitstempel liegt im Zielordner
- [ ] Eine Bilddatei von Hand umbenennen, eine löschen, eine fremde Datei reinkopieren → Reconcile findet alle drei richtig klassifiziert
- [ ] Repair „neu indizieren" auf die fremde Datei → erscheint in der Galerie
- [ ] `thumbnails.sqlite` von Hand löschen → Rebuild → Galerie zeigt wieder Thumbnails

## Summary

## Files touched

## Commits

## Deviations from plan

## Follow-ups
