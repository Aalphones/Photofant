# STATE

**Aktiver Plan:** `docs/planning/2026-06-30_p19-inference-session-pool/`
**Phase:** 2/4 abgeschlossen und committet — Phase 3 (VRAM-Budget-Rechner + API-Erweiterung) folgt
**Nächster Schritt:** `/clear`, dann `/model sonnet` (Phase 3 ist als „mechanisch" geratet),
danach `/implement p19` → `phase-3-vram-budget-api.md` lesen und umsetzen.

Offen aus Phase 1: manueller UI-Smoke-Test (ein Bild taggen + captionen über die App) —
noch nicht durchgeführt, siehe Report-Back in `phase-1-session-pool.md`.
Offen aus Phase 2: manuelle Worker-Parallelitäts-Tests (`tagging_workers=2` per Hand in
`settings.json`, Job-Dock beobachten) — noch nicht durchgeführt, siehe Report-Back in
`phase-2-settings-queue-workers.md`. Beide werden zusammen mit der finalen Smoke-Checkliste
am Plan-Ende geprüft, spätestens wenn Phase 4 den echten Slider liefert.

P29 (Personen-Suche/Filter/Gruppen) archiviert nach
`docs/archive/2026-07/2026-07-02_p29-personen-suche-gruppen/`. Offen aus P29:
Perf-Messung mit >300 Personen (Smoke-Checkliste in der archivierten README).
