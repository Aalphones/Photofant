# STATE

**Aktiver Plan:** `docs/planning/2026-07-03_p32-perf-personen-galerie.md`
**Phase:** 2/2 — noch nicht begonnen
**Nächster Schritt:** Phase 2 umsetzen — `GET /persons` ohne N+1 (Aggregat-Umbau in `api/persons.py`).

**Reihenfolge (kurzfristig eingeschoben, 2026-07-03):** P31 → P32 → P18 wird danach fortgesetzt.

- P31 (Duplikate: Schwelle fixen, Review paginieren) — **archiviert** nach
  `docs/archive/2026-07/2026-07-03_p31-duplikate-schwelle-pagination/`. Smoke-Checkliste dort
  noch offen (User prüft: Voll-Scan auf 8.440er-Bestand, Review-Pagination, Lightbox, Slider).
- P32 (Performance: Personen-Seite, -Suche, Galerie-Ballast) — `docs/planning/2026-07-03_p32-perf-personen-galerie.md`, 2 Phasen, alle pending.
- P18 (Bildklassifizierung) — pausiert bei Phase 2/6 (Engine: CLIP + WD14-Fusion, Job, Pipeline-Hook).
  Phase 1 (Datenmodell & Seed-Katalog) ist committet. Nach P31+P32: `docs/planning/2026-06-30_p18-bildklassifizierung/phase-2-engine-fusion.md`
  lesen und umsetzen. Rest im Backlog geparkt: p20, p22-p27.

P19 (Inference Session Pool) archiviert nach
`docs/archive/2026-07/2026-07-02_p19-inference-session-pool/`. Finale Smoke-Checkliste wurde
vom User bewusst übersprungen (nicht manuell getestet) — bei Symptomen (Hänger/stiller Crash
bei hoher Worker-Zahl, Slider verhält sich falsch) dort zuerst nachschauen.

P29 (Personen-Suche/Filter/Gruppen) archiviert nach
`docs/archive/2026-07/2026-07-02_p29-personen-suche-gruppen/`. Offen aus P29:
Perf-Messung mit >300 Personen (Smoke-Checkliste in der archivierten README).
