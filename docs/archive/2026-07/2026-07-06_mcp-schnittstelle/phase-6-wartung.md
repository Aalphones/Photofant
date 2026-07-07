# Phase 6 — Wartung + Confirmation-Gate scharfstellen

**Komplexität:** standard · **Status:** complete

## Kontext (vor dem Bauen lesen)

- `README.md` — Kontrakt, Gate (hier: `repair` bei `trash`/`mark_missing`).
- `phase-1` — `gate.py`.
- `backend/photofant/api/maintenance.py` — `backup` (`POST /maintenance/backup`), `list_backups`
  (`GET /maintenance/backups`), `reconcile` (`POST /maintenance/reconcile`), `reconcile_report`
  (`GET /maintenance/reconcile/report`), `repair` (`POST /maintenance/reconcile/repair`), `rebuild`
  (`POST /maintenance/rebuild`, target `thumbnails|embeddings|faces`), `status` (`GET /maintenance/status`).
- `docs/routes.md` — Abschnitt „Maintenance", inkl. `RebuildTarget` und `RepairAction`.

## AK (falsifizierbar)

- [x] `tools/maintenance.py` registriert:
  - [x] `rebuild(target)` → `POST /maintenance/rebuild`, `target ∈ {thumbnails, embeddings, faces}`
        (async → `job_id`). **Das ist „Gesichter neu extrahieren" (`target=faces`).** Kein Gate
        (regeneriert, löscht keine Nutzdaten).
  - [x] `backup(target_dir?)` → `POST /maintenance/backup` (async → `job_id`).
  - [x] `list_backups()` → `GET /maintenance/backups`.
  - [x] `maintenance_status()` → `GET /maintenance/status` (DB-Größe, Thumbnail-Count, Cache-Größe).
  - [x] `reconcile()` → `POST /maintenance/reconcile` (async → `job_id`); `reconcile_report()` →
        `GET /maintenance/reconcile/report` (Waisen/fehlende Dateien/Pfad-Drift).
  - [x] `repair(actions, confirm=false)` → `POST /maintenance/reconcile/repair`. **Gate**, sobald eine
        Aktion `trash` oder `mark_missing` enthält; reine `index`/`fix_path`-Aktionen laufen ohne Gate.
- [x] **Gesamt-Gate-Check:** alle in der README gelisteten Gate-Tools (Phasen 4–6) verweigern ohne
      `confirm=true` und respektieren `mcp.require_confirm=false` (dann direkt).

## Umsetzung — Checkliste

- [x] `tools/maintenance.py` mit den Tools oben; `repair`-Gate bedingt an der Aktionsart.
- [x] Regressions-Durchgang über alle Gate-Tools (confirm-Semantik + Setting).
- [x] Doc: `docs/routes.md` MCP-Abschnitt vervollständigen (alle Tools gelistet), `docs/code-map.md`
      final prüfen.

## Report-Back

`tools/maintenance.py` (132 Zeilen) mit 7 Tools: `rebuild`, `backup`, `list_backups`,
`maintenance_status`, `reconcile`, `reconcile_report`, `repair`. Vier Endpoints
(`trigger_backup`, `list_backups`, `trigger_reconcile`, `trigger_rebuild`) brauchen keine
DB-Session (reiner Job-Enqueue bzw. Dateisystem-Read) — direkter Aufruf statt
`run_endpoint()` (analog FINDINGS.md Phase 3/4/5/6: sync/session-lose Endpoints, hier:
session-lose statt sync). `repair`-Gate greift nur bei `trash`/`mark_missing`-Aktionen im
Batch, geprüft per Direktaufruf ohne DB-Touch (gated Pfad gibt die Warnung zurück, bevor
`run_endpoint()` überhaupt aufgerufen wird). Alle 63 Tools des Gesamtplans registrieren
fehlerfrei (`mcp_server.list_tools()`), ruff/mypy grün. `docs/routes.md` MCP-Tabelle
vervollständigt (Phase 6 ergänzt, Tabelle geschlossen), `docs/code-map.md` bereits ordner-grob
genug (`tools/` deckt neue Module ab, keine Änderung nötig). Kein Live-MCP-Handshake in dieser
Phase (private-Profil: Smoke einmal am Plan-Ende) — bleibt weiterhin die oberste Wackelstelle
seit Phase 1.
