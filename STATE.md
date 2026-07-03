# STATE

**Aktiver Plan:** `docs/planning/2026-07-03_editor-basis-fixes.md`
**Phase:** 3/3 — Backend-Risiko-Phase: Orientierung (Dreh/Spiegeln) überschreibt die Quelle
statt neue Version anzulegen.
**Nächster Schritt:** Plan-Datei lesen, bbox-Transform-Helfer + `save_session`-Zweig für
Orientierungs-only-Sessions bauen (Details/Risiken stehen im Plan).

**Reihenfolge (kurzfristig eingeschoben, 2026-07-03):** P31 → P32 erledigt, Editor-Basis-Fixes
zwischengeschoben (Phase 1+2 committet), danach P18 fortsetzen.

- P31 (Duplikate: Schwelle fixen, Review paginieren) — archiviert nach
  `docs/archive/2026-07/2026-07-03_p31-duplikate-schwelle-pagination/`. Smoke-Checkliste dort
  noch offen (User prüft: Voll-Scan auf 8.440er-Bestand, Review-Pagination, Lightbox, Slider).
- P32 (Performance: Personen-Seite, -Suche, Galerie-Ballast) — **archiviert** nach
  `docs/archive/2026-07/2026-07-03_p32-perf-personen-galerie.md`. Smoke-Checkliste dort noch
  offen (User prüft: Personen-Seite schnell, Counts/Favoriten/Portraits stimmen, Person-Filter
  + Freitextsuche + Tag-Filter schnell, tiefes Scrollen flüssig, semantische Suche + Face-Match
  funktionieren).
- Editor-Basis-Fixes (Speichern verdrahten, Crop-Ratio, Leisten-Breite) — Phase 1+2 committet,
  Phase 3 (Backend: Orientierung überschreibt Quelle) jetzt dran.
- P18 (Bildklassifizierung) — Phase 1 (Datenmodell & Seed-Katalog) committet, Phase 2 pausiert
  bis Editor-Basis-Fixes durch sind. Rest im Backlog geparkt: p20, p22-p27.

**Unabhängig im Working Tree liegen gelassen (nicht Teil eines aktiven Plans):** ein fertig
wirkender „stranded_face"-Reparatur-Fix (Backend + Reconcile-UI + Tests, verirrte
Gesichts-Crops zurück ins richtige Personen-Verzeichnis) — auf User-Wunsch unangetastet.
Bei Bedarf eigenständig committen oder in einen Plan aufnehmen.

P19 (Inference Session Pool) archiviert nach
`docs/archive/2026-07/2026-07-02_p19-inference-session-pool/`. Finale Smoke-Checkliste wurde
vom User bewusst übersprungen (nicht manuell getestet) — bei Symptomen (Hänger/stiller Crash
bei hoher Worker-Zahl, Slider verhält sich falsch) dort zuerst nachschauen.

P29 (Personen-Suche/Filter/Gruppen) archiviert nach
`docs/archive/2026-07/2026-07-02_p29-personen-suche-gruppen/`. Offen aus P29:
Perf-Messung mit >300 Personen (Smoke-Checkliste in der archivierten README).
