# STATE

**Aktiver Plan:** `docs/planning/2026-06-30_p18-bildklassifizierung/phase-2-engine-fusion.md`
**Phase:** 2/6 — Engine: CLIP + WD14-Fusion, Job, Pipeline-Hook
**Nächster Schritt:** Phase-2-Datei lesen (Kontext-Diät: README + eigene Phasen-Datei + FINDINGS) und Engine umsetzen.

**Reihenfolge (kurzfristig eingeschoben, 2026-07-03):** P31 → P32 erledigt, P18 wird jetzt fortgesetzt.

- P31 (Duplikate: Schwelle fixen, Review paginieren) — archiviert nach
  `docs/archive/2026-07/2026-07-03_p31-duplikate-schwelle-pagination/`. Smoke-Checkliste dort
  noch offen (User prüft: Voll-Scan auf 8.440er-Bestand, Review-Pagination, Lightbox, Slider).
- P32 (Performance: Personen-Seite, -Suche, Galerie-Ballast) — **archiviert** nach
  `docs/archive/2026-07/2026-07-03_p32-perf-personen-galerie.md`. Smoke-Checkliste dort noch
  offen (User prüft: Personen-Seite schnell, Counts/Favoriten/Portraits stimmen, Person-Filter
  + Freitextsuche + Tag-Filter schnell, tiefes Scrollen flüssig, semantische Suche + Face-Match
  funktionieren).
- P18 (Bildklassifizierung) — Phase 1 (Datenmodell & Seed-Katalog) committet, Phase 2 jetzt dran.
  Rest im Backlog geparkt: p20, p22-p27.

P19 (Inference Session Pool) archiviert nach
`docs/archive/2026-07/2026-07-02_p19-inference-session-pool/`. Finale Smoke-Checkliste wurde
vom User bewusst übersprungen (nicht manuell getestet) — bei Symptomen (Hänger/stiller Crash
bei hoher Worker-Zahl, Slider verhält sich falsch) dort zuerst nachschauen.

P29 (Personen-Suche/Filter/Gruppen) archiviert nach
`docs/archive/2026-07/2026-07-02_p29-personen-suche-gruppen/`. Offen aus P29:
Perf-Messung mit >300 Personen (Smoke-Checkliste in der archivierten README).
