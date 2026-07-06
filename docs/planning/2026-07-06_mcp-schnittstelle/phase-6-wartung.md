# Phase 6 — Wartung + Confirmation-Gate scharfstellen

**Komplexität:** standard · **Status:** pending

## Kontext (vor dem Bauen lesen)

- `README.md` — Kontrakt, Gate (hier: `repair` bei `trash`/`mark_missing`).
- `phase-1` — `gate.py`.
- `backend/photofant/api/maintenance.py` — `backup` (`POST /maintenance/backup`), `list_backups`
  (`GET /maintenance/backups`), `reconcile` (`POST /maintenance/reconcile`), `reconcile_report`
  (`GET /maintenance/reconcile/report`), `repair` (`POST /maintenance/reconcile/repair`), `rebuild`
  (`POST /maintenance/rebuild`, target `thumbnails|embeddings|faces`), `status` (`GET /maintenance/status`).
- `docs/routes.md` — Abschnitt „Maintenance", inkl. `RebuildTarget` und `RepairAction`.

## AK (falsifizierbar)

- [ ] `tools/maintenance.py` registriert:
  - [ ] `rebuild(target)` → `POST /maintenance/rebuild`, `target ∈ {thumbnails, embeddings, faces}`
        (async → `job_id`). **Das ist „Gesichter neu extrahieren" (`target=faces`).** Kein Gate
        (regeneriert, löscht keine Nutzdaten).
  - [ ] `backup(target_dir?)` → `POST /maintenance/backup` (async → `job_id`).
  - [ ] `list_backups()` → `GET /maintenance/backups`.
  - [ ] `maintenance_status()` → `GET /maintenance/status` (DB-Größe, Thumbnail-Count, Cache-Größe).
  - [ ] `reconcile()` → `POST /maintenance/reconcile` (async → `job_id`); `reconcile_report()` →
        `GET /maintenance/reconcile/report` (Waisen/fehlende Dateien/Pfad-Drift).
  - [ ] `repair(actions, confirm=false)` → `POST /maintenance/reconcile/repair`. **Gate**, sobald eine
        Aktion `trash` oder `mark_missing` enthält; reine `index`/`fix_path`-Aktionen laufen ohne Gate.
- [ ] **Gesamt-Gate-Check:** alle in der README gelisteten Gate-Tools (Phasen 4–6) verweigern ohne
      `confirm=true` und respektieren `mcp.require_confirm=false` (dann direkt).

## Umsetzung — Checkliste

- [ ] `tools/maintenance.py` mit den Tools oben; `repair`-Gate bedingt an der Aktionsart.
- [ ] Regressions-Durchgang über alle Gate-Tools (confirm-Semantik + Setting).
- [ ] Doc: `docs/routes.md` MCP-Abschnitt vervollständigen (alle Tools gelistet), `docs/code-map.md`
      final prüfen.

## Report-Back
