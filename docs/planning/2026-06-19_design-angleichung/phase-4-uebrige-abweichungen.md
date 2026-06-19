# Phase 4 — Übrige bestätigte Abweichungen

> Rating: standard · Status: pending

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

## Checkliste (wird aus Phase 1 gefüllt — Beispiele/Verdachtsmomente)

- [ ] Shell: Storage-Indikator in der Nav-Rail (Mockup) — fehlt vermutlich; Backend-Bedarf klären
- [ ] Sub-Toolbar: Filter-Chip-Differenzierung Kategorie- vs. Feature-Chips (`.accent`)
- [ ] _(weitere Punkte aus `design-reconciliation.md` eintragen)_
- [ ] Doc-Update: `design-reconciliation.md` Punkte abhaken; betroffene `routes.md`/`models.md` falls Backend berührt

## Report-Back
