# STATE

**Aktiver Plan:** `docs/planning/2026-06-30_p19-inference-session-pool/`
**Phase:** 3/4 abgeschlossen und committet — Phase 4 (Frontend: Worker-Slider) folgt
**Nächster Schritt:** `/clear`, dann `/model sonnet` (Phase 4 ist „standard"),
danach `/implement p19` → `phase-4-frontend-slider.md` lesen und umsetzen.

Offen aus Phase 1: manueller UI-Smoke-Test (ein Bild taggen + captionen über die App) —
noch nicht durchgeführt, siehe Report-Back in `phase-1-session-pool.md`.
Offen aus Phase 2: manuelle Worker-Parallelitäts-Tests (`tagging_workers=2` per Hand in
`settings.json`, Job-Dock beobachten) — noch nicht durchgeführt, siehe Report-Back in
`phase-2-settings-queue-workers.md`.
Offen aus Phase 3: `GET /api/models/vram` zeigt die neuen `suggested_*_workers`-Felder erst
nach Backend-Neustart (laufender Prozess serviert alten Stand); Formeln sind mit echter GPU
verifiziert (RTX 3060, 12 GB → 4/4). Alle drei offenen Punkte werden mit der finalen
Smoke-Checkliste am Plan-Ende geprüft — Phase 4 braucht den Endpoint ohnehin live.

P29 (Personen-Suche/Filter/Gruppen) archiviert nach
`docs/archive/2026-07/2026-07-02_p29-personen-suche-gruppen/`. Offen aus P29:
Perf-Messung mit >300 Personen (Smoke-Checkliste in der archivierten README).
