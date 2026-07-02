# STATE

**Aktiver Plan:** `docs/planning/2026-07-02_p29-personen-suche-gruppen/`
**Phase:** 3/6 — Frontend Store: Persistenz für Gruppen-Zuweisung (pending)
**Nächster Schritt:** Phase-3-Checkliste in `phase-3-store-persistenz.md` abarbeiten.
Phase 2 fertig: `Person.group_name`/`created_at` (Migration 0026), `PersonDto` erweitert,
`PATCH /persons/{id}` nimmt jetzt `name`/`group_name` unabhängig entgegen (422 wenn beides
leer). Backend ruff+pytest sauber (12 vorbestehende, unabhängige ComfyUI-Test-Fehler ignoriert).
Doc-Updates (`docs/models.md`, `docs/routes.md`) erledigt.
Committen steht noch aus (`mode-committing`), danach `/clear` vor Phase 3.
