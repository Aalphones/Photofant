# Findings

Einträge werden während der Umsetzung hier getaggt:
`- [ ] → Phase N: <Erkenntnis / Folgeaufgabe>`

- [ ] → Phase 3: `_st-shared.scss` enthält noch alle `st-*` Utility-Klassen ungeteilt. Phase 3 entscheidet, welche Klassen echtes BEM pro Komponente bekommen und welche als globale Utilities verbleiben. Aktuell binden alle 8 Child-SCSSes die Datei komplett ein (CSS-Duplikat im Bundle, funktional korrekt).
- [ ] → Phase 3: `tags`-Komponente war nicht im ursprünglichen 7-Komponenten-Plan. Wurde hinzugefügt, weil SECTIONS 8 Einträge hat. Kein Impact auf Plan-Ziele, aber BEM-Checkliste in Phase 3 muss `tags__*` einschließen.
