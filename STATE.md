# STATE

**Aktiver Plan:** P18 (Bildklassifizierung) — `docs/planning/2026-06-30_p18-bildklassifizierung/`
**Phase:** 3/6 — Backend-API: CRUD, Retro-Lauf, Filter/Facets/Suche (`phase-3-backend-api-suche.md`)
**Nächster Schritt:** Phase 3 starten. Aus FINDINGS.md zu beachten: SQLite fährt
`ON DELETE CASCADE` nur mit `PRAGMA foreign_keys=ON` (projektweit aktuell aus) — beim Löschen
einer Kategorie/eines Labels die Kind-Zeilen (`classification_label`, `asset_classification`)
explizit im Python-Code mitlöschen.

**Reihenfolge (kurzfristig eingeschoben, 2026-07-03):** P31 → P32 → Editor-Basis-Fixes
(alle 3 Phasen) erledigt, jetzt zurück zu P18.

- P31 (Duplikate: Schwelle fixen, Review paginieren) — archiviert nach
  `docs/archive/2026-07/2026-07-03_p31-duplikate-schwelle-pagination/`. Smoke-Checkliste dort
  noch offen (User prüft: Voll-Scan auf 8.440er-Bestand, Review-Pagination, Lightbox, Slider).
- P32 (Performance: Personen-Seite, -Suche, Galerie-Ballast) — **archiviert** nach
  `docs/archive/2026-07/2026-07-03_p32-perf-personen-galerie.md`. Smoke-Checkliste dort noch
  offen (User prüft: Personen-Seite schnell, Counts/Favoriten/Portraits stimmen, Person-Filter
  + Freitextsuche + Tag-Filter schnell, tiefes Scrollen flüssig, semantische Suche + Face-Match
  funktionieren).
- Editor-Basis-Fixes (Speichern verdrahten, Crop-Ratio, Leisten-Breite, Orientierung
  überschreibt Quelle) — **archiviert** nach
  `docs/archive/2026-07/2026-07-03_editor-basis-fixes.md`. Smoke-Checkliste dort noch offen
  (User prüft: Speichern schließt den Editor & zeigt das Ergebnis, Crop-Ratio-Buttons treffen
  das echte Seitenverhältnis, Werkzeug-Leiste ist breiter, Drehen/Spiegeln überschreibt die
  Datei ohne Modal-Nachfrage — auch bei einem Mehrpersonen-Foto, wo alle beteiligten Personen
  danach noch die gedrehte Version sehen).
- P18 (Bildklassifizierung) — Phase 1 (Datenmodell & Seed-Katalog) + Phase 2 (Engine:
  CLIP+WD14-Fusion, Job, Pipeline-Hook) committet, Phase 3 jetzt dran. Rest im Backlog
  geparkt: p20, p22-p27.

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
