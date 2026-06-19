# FINDINGS — Design-Angleichung

Erkenntnisse über Phasengrenzen hinweg. Append-only, jeder Eintrag mit Ziel-Tag.

<!-- Format: - [ ] → Phase N: <Erkenntnis, 1-3 Zeilen — was wurde entdeckt, was heißt das für die Ziel-Phase> -->

## Vorab bekannt (aus der Voranalyse 2026-06-19, vor Plan-Erstellung)

- [x] → Phase 2: Einstellungen sind heute **flacher Einspalten-Scroll** (`einstellungen.ts:25-255`, `settings-layout` `max-width:680`), nicht das `st-page`-Master-Detail des Mockups (`settings.jsx:504-518`). Ursache: kein Plan besaß je die Settings-IA; Sektionen wurden von P03/P04/settings-json einzeln angebaut. ← eingearbeitet in Phase-2-Finding unten
- [x] → Phase 3: Tags-Seite hat **kein Mockup**, nur Nav-Slot `app.jsx:63`. Gebaut nach Konzept §10 (`P6 phase-3-tag-verwaltung.md:14`), dessen Kontext-Sektion `docs/design` gar nicht listet → Optik freihändig erfunden. ← bestätigt durch Phase 1
- [x] → Phase 4: Nav-Rail-Storage-Indikator statisch (bestätigt KLEIN); Sub-Toolbar-Filter-Chips ohne Kategorie-Prefix (bestätigt KLEIN). ← eingearbeitet in Phase-4-Findings unten
- [x] → Phase 1: Backlog sauber abgrenzen — P7-Faces (Lightbox-Gesichter-Strip), P8-Versionen (Versionen-Timeline) als sauber-verschoben klassifiziert. ← erledigt in design-reconciliation.md

## Aus Phase 1 — Reconciliation-Sweep (2026-06-19)

- [x] → Phase 2: **Einstellungen-Shell fehlt `st-page`-Master-Detail** (`einstellungen.ts:41-43`). Impl ist `settings-layout` single-column (max-width 680px, vertikaler Scroll). Design ist `st-page` mit linker `st-nav` (Sektions-Nav mit Icons) + rechter `st-body`. Beide Layout-Ebenen müssen gebaut werden. Bestehende Sektions-Inhalte (Darstellung, Bibliothek, Verarbeitung, Caption-Presets, Tastaturkürzel, Info, Backup) in die neue Shell einziehen — Funktionen erhalten.

- [x] → Phase 3: **Tags kein Mockup, Design freihändig erfunden** (`tags.html`). ← ADR-005: Re-home in Einstellungen — `/tags`-Route + Feature entfernt, Sektion in `einstellungen.ts` eingefaltet.

- [ ] → Phase 4: **Filter-Rail — Person-Facette fehlt (GROSS).** Im Design erste Facette (`gallery.jsx:38-49`), in Impl (`filter-rail.html`) gar nicht vorhanden. Benötigt: Person-Avatare als Facetten-Rows, Person-IDs als Filter-Parameter, Backend-Endpunkt für Person-Counts.

- [ ] → Phase 4: **Filter-Rail — Framing-Facette fehlt (GROSS).** Design: `gallery.jsx:58-62` (close_up / medium / full_body). In `filter-rail.html` nicht vorhanden.

- [ ] → Phase 4: **Grid-Zelle — Person-Avatar fehlt (MITTEL).** Design hat `tile-person` Avatar (22 px) oben-links in jeder Zelle (`gallery.jsx:122-123`). `cell.html` zeigt keinen Avatar.

- [ ] → Phase 4: **Nav-Rail — Favoriten-Item fehlt (MITTEL).** Design: `app.jsx:21` — eigenständiger Nav-Eintrag `id="favourites"` mit Fav-Count-Badge. Impl (`nav-rail.ts:29-35`) hat keinen solchen Eintrag und keine `/favoriten`-Route.

- [ ] → Phase 4: **Nav-Rail — Review-Queue-Item fehlt (MITTEL).** Design: `app.jsx:25` — `id="review"` unter Verwaltung. Keine Route, kein Nav-Item, keine Feature-Komponente.

- [ ] → Phase 4: **Mobile Nav — Tab-Auswahl abweichend (MITTEL).** Design: [Galerie, Personen, Favoriten, Mehr]. Impl (`shell.html:51-68`): [Galerie, Personen, Alben, Einstellungen]. Favoriten-Tab fehlt; Mehr-Overlay-Pattern fehlt (stattdessen direkte Links zu Alben/Einstellungen).

- [ ] → Phase 4: **Sub-Toolbar — Auswählen-Button ausgelagert (MITTEL).** Design: Teil von `sb-tools` im Subbar (`gallery.jsx:237-238`). Impl: separater `galerie__sel-bar` außerhalb der Sub-Toolbar (`galerie.html:11-19`).

- [ ] → Phase 4: **Nav-Rail — Storage-Indikator statisch (KLEIN).** Impl zeigt "Bibliothek leer · 0%" hardcoded (`nav-rail.html:44-54`). Design zeigt echte Werte (GB, Asset-Count, %).

- [ ] → Phase 4: **Sub-Toolbar — Chips ohne Kategorie-Prefix (KLEIN).** Design zeigt "Person:", "Quelle:" als `chip-key` vor Label (`gallery.jsx:219`). Impl (`sub-toolbar.html:13`) zeigt nur Label.
