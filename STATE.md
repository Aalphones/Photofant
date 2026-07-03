# STATE

**Aktiver Plan:** `docs/planning/2026-07-03_p31-duplikate-schwelle-pagination/`
**Phase:** 1/3 — Threshold-Semantik & Entkopplung (offen)
**Nächster Schritt:** `phase-1-threshold-semantik.md` lesen und umsetzen.

**Reihenfolge (kurzfristig eingeschoben, 2026-07-03):** P31 → P32 → P18 wird danach fortgesetzt.

- P31 (Duplikate: Schwelle fixen, Review paginieren) — `docs/planning/2026-07-03_p31-duplikate-schwelle-pagination/`, 3 Phasen, alle pending.
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
