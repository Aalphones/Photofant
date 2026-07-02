# STATE

**Aktiver Plan:** `docs/planning/2026-07-02_p29-personen-suche-gruppen/`
**Phase:** 2/5 — Backend: Gruppenfeld + Erstellungsdatum (pending)
**Nächster Schritt:** Phase-2-Checkliste in `phase-2-backend-gruppenfeld.md` abarbeiten
(Alembic-Migration + `Person.group_name`/`created_at` + `PATCH /persons/{id}`).
Phase 1 fertig: `run_initial_clustering` matcht unbekannte Gesichter jetzt zuerst gegen
bestehende Personen (auto/review/unknown-Band), erst der Rest geht durch HDBSCAN.
Backend ruff+pytest sauber (12 vorbestehende, unabhängige ComfyUI-Test-Fehler ignoriert).
Committen steht noch aus (`mode-committing`), danach `/clear` vor Phase 2.
