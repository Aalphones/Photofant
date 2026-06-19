# FINDINGS — Design-Angleichung

Erkenntnisse über Phasengrenzen hinweg. Append-only, jeder Eintrag mit Ziel-Tag.

<!-- Format: - [ ] → Phase N: <Erkenntnis, 1-3 Zeilen — was wurde entdeckt, was heißt das für die Ziel-Phase> -->

## Vorab bekannt (aus der Voranalyse 2026-06-19, vor Plan-Erstellung)

- [ ] → Phase 2: Einstellungen sind heute **flacher Einspalten-Scroll** (`einstellungen.ts:25-255`, `settings-layout` `max-width:680`), nicht das `st-page`-Master-Detail des Mockups (`settings.jsx:504-518`). Ursache: kein Plan besaß je die Settings-IA; Sektionen wurden von P03/P04/settings-json einzeln angebaut.
- [ ] → Phase 3: Tags-Seite hat **kein Mockup**, nur Nav-Slot `app.jsx:63`. Gebaut nach Konzept §10 (`P6 phase-3-tag-verwaltung.md:14`), dessen Kontext-Sektion `docs/design` gar nicht listet → Optik freihändig erfunden.
- [ ] → Phase 4: Verdacht (vom Explore-Sweep, **unbestätigt** — in Phase 1 verifizieren): Nav-Rail-Storage-Indikator fehlt; Sub-Toolbar-Filter-Chips ohne Kategorie-/Feature-Differenzierung. Beides KLEIN/MITTEL.
- [ ] → Phase 1: Backlog sauber abgrenzen — P7-Faces (Lightbox-Gesichter-Strip), P8-Versionen (Versionen-Timeline), fehlende Einstellungs-Sektionen sind **verschoben, keine Abweichung**.
