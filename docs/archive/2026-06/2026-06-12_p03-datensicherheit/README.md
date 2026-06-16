# P3 — Datensicherheit (Querschnitt)

> Status: geparkt · Quelle: [Konzept](../../Konzept-Photofant.md) §13, §18 Querschnitt · Abhängigkeiten: P2

Die DB ist die alleinige Metadaten-Wahrheit (bewusst akzeptiertes Risiko) — dieser Plan liefert die Absicherung: Backup, FS↔DB-Abgleich, Cache-Rebuild. Früh nach P2, weil manuell eingeschobene Dateien ab sofort Drift erzeugen können.

## Overview

| Phase | Topic | Rating | Status |
|---|---|---|---|
| 1 | [DB-Backup](phase-1-db-backup.md) | mechanisch | complete |
| 2 | [FS↔DB-Reconciliation](phase-2-reconciliation.md) | heikel | complete |
| 3 | [Rebuild & Wartungs-View](phase-3-rebuild-wartung.md) | standard | complete |

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

Datensicherheits-Querschnitt vollständig: DB-Backup (SQLite Online Backup API),
FS↔DB-Reconciliation mit Repair-Aktionen, und Thumbnail-Cache-Rebuild — alles über
die UI, kein Skript nötig. Backup lebt in `Einstellungen`, Scan + Rebuild + Status
auf einer eigenen `/wartung`-Seite nach Design-Prototyp.

## Files touched

**Backend** — `jobs/queue.py` (REBUILD-Kind), `jobs/thumbnail_job.py` (geteilter
`generate_thumbnails`-Helper), `jobs/rebuild_job.py` (neu), `db/cache.py`
(`count_thumbnail_targets`), `api/maintenance.py` (`/rebuild` + `/status`).

**Frontend** — `models/maintenance.model.ts` + `models/job.model.ts` (`'rebuild'`),
`services/maintenance.service.ts`, `store/maintenance/*` (actions/reducer/selectors/effects),
`features/wartung/wartung.ts` (neu), `features/einstellungen/einstellungen.ts` (auf Backup
reduziert), `shell/nav-rail/nav-rail.ts`, `app.routes.ts`, `models/index.ts`.

**Docs** — `routes.md` (Rebuild/Status-Endpoints, `/wartung`-Route, `MaintenanceStatus`).

## Commits

- Phase 1 — `b2656fa` DB-Backup via SQLite Online Backup API
- Phase 2 — `283fc83` FS↔DB-Reconciliation
- Phase 3 — _siehe Git-Log nach diesem Commit_

## Deviations from plan

- Wartungs-View als **eigene Route** statt in `Einstellungen` (User-Entscheidung, Prototyp-treu); Backup bleibt in `Einstellungen`.
- **Kein** Cancel-Button für Rebuild — „abbrechbar ohne Schaden" ist by-design erfüllt (Cache-only), Prototyp hat ebenfalls keinen.
- Bulk-Select im Scan weggelassen (laut Findings optionaler Komfort, nicht in den AK).

## Follow-ups

- **P7/P8:** Reconcile um Face-/Edit-Tabellen erweitern; Face-Rebuild-Target + Face-Status-Stat (heute „ab P7").
- **Cleanup:** `formatSize` existiert in 6+ Komponenten dupliziert → in einen geteilten Util/Pipe ziehen.
- 🟡 Wartung-Komponenten-CSS überschreitet das 4-kB-Budget um 722 B (geduldete Warnung).
