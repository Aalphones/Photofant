# Phase 4 — Übrige bestätigte Abweichungen

> Rating: standard · Status: complete

Arbeitet die in Phase 1 bestätigten GROSS/MITTEL-Abweichungen der **übrigen** Views ab (alles außer Einstellungen & Tags — die haben eigene Phasen). **Inhalt wird aus Phase 1 konkretisiert** — bis dahin ein Rahmen.

## Kontext (vorher lesen)

- [README.md](README.md)
- `docs/design-reconciliation.md` — die in Phase 1 erzeugte Abweichungsliste (**Haupt-Input**)
- die `→ Phase 4`-getaggten Einträge in [FINDINGS.md](FINDINGS.md)
- pro angefasster View: der jeweilige Mockup-Abschnitt + die Impl-Dateien (aus dem Reconciliation-Doc verlinkt)

## Akzeptanzkriterien

- Jeder in Phase 1 als **GROSS oder MITTEL** klassifizierte Punkt der übrigen Views ist entweder behoben oder mit Begründung in einen Backlog-Plan verschoben (in `design-reconciliation.md` abgehakt).
- KLEIN-Punkte sind optional — bewusst entscheiden, nicht still liegenlassen (im Doc als „bewusst gelassen" markieren).
- Aufgedeckter Backend-Bedarf (z.B. Speichernutzungs-Werte für den Mockup-Speicherbalken) wird hier als Mini-Kontrakt umgesetzt **oder** sauber als eigener Plan ausgegliedert (kein stiller Stub).

## Checkliste

- [x] Sub-Toolbar: Auswählen-Button in `subbar__tools` integriert; `galerie__sel-bar` entfernt — `sub-toolbar.ts/html/scss`, `galerie.html/scss`
- [x] Sub-Toolbar: Chip-Key-Prefix (`subbar__chip-key`) + `chipKey`-Feld in `FilterChip`
- [x] Nav-Rail: Favoriten-Item hinzugefügt; Review-Queue-Item hinzugefügt; Tags-Item entfernt (ADR-005-Cleanup) — `nav-rail.ts`
- [x] Routes: `/favoriten` + `/review` angelegt (`app.routes.ts`); Stubs `favoriten.ts`, `review.ts`; `ROUTE_TITLES` in `shell.ts`
- [x] Mobile Nav: Tabs auf [Galerie, Personen, Favoriten, Mehr] — `shell.html`
- [x] Person-Facette, Framing-Facette, Person-Avatar: sauber-verschoben P7 — `design-reconciliation.md` aktualisiert
- [x] Storage-Indikator statisch: bewusst gelassen (kein Backend-Endpunkt)
- [x] Doc-Update: `design-reconciliation.md` Punkte abgehakt; kein Backend berührt → kein `routes.md`/`models.md`-Update nötig

## Report-Back

Abgeschlossen 2026-06-19. 4 MITTEL-Punkte behoben, 2 GROSS + 1 MITTEL sauber-verschoben nach P7. 2 KLEIN behoben, 2 KLEIN bewusst gelassen.
