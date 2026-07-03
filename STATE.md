# STATE

**Aktiver Plan:** keiner — P18 (Bildklassifizierung) komplett fertig und archiviert nach
`docs/archive/2026-07/2026-06-30_p18-bildklassifizierung/`.
**Nächster Schritt:** Rest im Backlog geparkt (p20, p22-p27) — nächsten Plan mit dem User
abstimmen. Smoke-Checkliste P18 an User (siehe unten).

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
- P18 (Bildklassifizierung) — **fertig, alle 6 Phasen committet, Plan archiviert** nach
  `docs/archive/2026-07/2026-06-30_p18-bildklassifizierung/`. Phase 1 (Datenmodell &
  Seed-Katalog) + Phase 2 (Engine: CLIP+WD14-Fusion, Job, Pipeline-Hook) + Phase 3
  (Backend-API: CRUD, Filter/Facets/Suche, explizites Cascade-Delete) + Phase 4
  (Einstellungen-Tab Frontend: Shell + Kategorie-Editor, CRUD über store/classification,
  „Bestehende Bilder klassifizieren" verdrahtet) + Phase 5 (Galerie-Filter-Rail je Kategorie,
  Lightbox-Sektion „Klassifizierung", Such-Autocomplete für Labels) + Phase 6 (Docs:
  models.md/routes.md/code-map.md aktualisiert, ADR-010 angelegt, docs/glossary.md neu
  angelegt — existierte vorher nicht —, PROJECT.md-Meilenstein ergänzt). Smoke-Checkliste
  noch offen (User prüft: Einstellungen-Tab „Klassifizierung" — Kategorien/Labels
  anlegen/bearbeiten/löschen; „Bestehende Bilder klassifizieren" läuft durch; Lightbox zeigt
  Klassifizierungs-Sektion; Galerie-Filter-Rail hat je Kategorie eine Gruppe mit Facet-Counts;
  Suche findet Bilder über Label-Namen). Rest im Backlog geparkt: p20, p22-p27.

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
