# Phase 4 — Politur: Zusatz-Sortierungen, Empty-States, Perf-Check

**Tier:** standard
**Status:** complete (Perf-Messung mit echten Daten steht beim User aus, siehe Checkliste)
**Voraussetzung:** Phase 3 abgeschlossen

Abtrennbare Erweiterungen — falls nach Phase 3 erstmal Ruhe sein soll, bleibt
diese Phase einfach im Backlog liegen.

---

## Kontext (vorher lesen)

- `frontend/src/app/features/personen/personen.ts` — `SORT_CYCLE`, `personGroups()`
- `docs/planning/2026-06-30_p20-virtual-scroll-galerie/` — falls vorhanden: Vorlage, falls Virtualisierung nötig wird

---

## Abnahme-Kriterien

- [x] Zusätzliche Sortierungen „Unbenannt zuerst" und „Anzahl Fotos" verfügbar
- [x] Leere Gruppen (z.B. nach Filter-Kombination ohne Treffer) zeigen einen dezenten Empty-State statt einer leeren Fläche
- [ ] Bei sehr vielen Personen (Richtwert: > 300) bleibt die Seite flüssig — gemessen, nicht geraten (**offen — Messung durch User, siehe unten**)

---

## Checkliste

### personen.ts — erweiterter Sortier-Zyklus

- [x] `PersonSortKey` erweitern: `'group' | 'created' | 'name' | 'unnamed' | 'count'`
- [x] `SORT_CYCLE` und `sortLabel()` entsprechend ergänzen
- [x] `sortedPersons()` — neue Zweige (unnamed, count)

### personen.html — Empty-States pro Gruppe/Filter

- [x] Wenn `filteredPersons().length === 0` und Suche/Filter aktiv: „Keine Personen gefunden" statt der generellen Leerstate
- [x] Unterscheidung von der bestehenden „Noch keine Personen erkannt"-Leerstate (die bleibt für den Fall ganz ohne Personen)

### Performance-Check

- [x] `computed()`-Ketten geprüft: `filteredPersons` → `sortedPersons` → `personGroups` sind Angular-`computed()`-Signals, werden gecacht und nur bei Dependency-Änderung neu berechnet — auch bei Mehrfach-Referenz im Template (Grid + Alphabet-Rail) keine doppelte Neuberechnung pro Render-Zyklus. Kein struktureller Fix nötig.
- [ ] **Offen — braucht echte Daten:** Mit realistischer Personenzahl (> 300, Test-DB oder Produktions-Kopie) Scroll-Ruckeln/Such-Tipp-Latenz messen. Kann ich agentenlos ohne laufende App mit echtem Datenbestand nicht simulieren — bitte einmal in der laufenden App gegenprüfen. Falls ruckelig: virtuelles Scrollen nachziehen (Vorlage: P20, falls im Repo vorhanden).

---

## Doc-Updates

- [x] Keine neuen Settings-Keys
- [x] FINDINGS.md: Messergebnisse aus dem Performance-Check festhalten (Entscheidung dokumentiert, Live-Messung durch User offen)
