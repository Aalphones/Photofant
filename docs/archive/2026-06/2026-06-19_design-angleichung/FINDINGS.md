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

- [x] → Phase 4: **Filter-Rail — Person-Facette fehlt (GROSS).** → sauber-verschoben P7 (benötigt `person_id` auf AssetDto + Personen-API).

- [x] → Phase 4: **Filter-Rail — Framing-Facette fehlt (GROSS).** → sauber-verschoben P7 (benötigt `framing`-Feld aus AI-Analyse).

- [x] → Phase 4: **Grid-Zelle — Person-Avatar fehlt (MITTEL).** → sauber-verschoben P7 (benötigt `person_id` auf AssetDto).

- [x] → Phase 4: **Nav-Rail — Favoriten-Item fehlt (MITTEL).** → behoben: `nav-rail.ts` + `/favoriten`-Route + Stub `favoriten.ts`.

- [x] → Phase 4: **Nav-Rail — Review-Queue-Item fehlt (MITTEL).** → behoben: `nav-rail.ts` + `/review`-Route + Stub `review.ts`.

- [x] → Phase 4: **Mobile Nav — Tab-Auswahl abweichend (MITTEL).** → behoben: `shell.html` auf [Galerie, Personen, Favoriten, Mehr] umgestellt; Mehr öffnet Nav-Rail.

- [x] → Phase 4: **Sub-Toolbar — Auswählen-Button ausgelagert (MITTEL).** → behoben: Button in `sub-toolbar.html` `subbar__tools` integriert; `galerie__sel-bar` + Styles entfernt.

- [x] → Phase 4: **Nav-Rail — Storage-Indikator statisch (KLEIN).** → bewusst gelassen (kein Backend-Endpunkt).

- [x] → Phase 4: **Sub-Toolbar — Chips ohne Kategorie-Prefix (KLEIN).** → behoben: `chipKey` in `FilterChip` + `subbar__chip-key`-Span.
