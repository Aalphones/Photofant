# Phase 4 — Politur: Zusatz-Sortierungen, Empty-States, Perf-Check

**Tier:** standard
**Status:** pending
**Voraussetzung:** Phase 3 abgeschlossen

Abtrennbare Erweiterungen — falls nach Phase 3 erstmal Ruhe sein soll, bleibt
diese Phase einfach im Backlog liegen.

---

## Kontext (vorher lesen)

- `frontend/src/app/features/personen/personen.ts` — `SORT_CYCLE`, `personGroups()`
- `docs/planning/2026-06-30_p20-virtual-scroll-galerie/` — falls vorhanden: Vorlage, falls Virtualisierung nötig wird

---

## Abnahme-Kriterien

- [ ] Zusätzliche Sortierungen „Unbenannt zuerst" und „Anzahl Fotos" verfügbar
- [ ] Leere Gruppen (z.B. nach Filter-Kombination ohne Treffer) zeigen einen dezenten Empty-State statt einer leeren Fläche
- [ ] Bei sehr vielen Personen (Richtwert: > 300) bleibt die Seite flüssig — gemessen, nicht geraten

---

## Checkliste

### personen.ts — erweiterter Sortier-Zyklus

- [ ] `PersonSortKey` erweitern: `'group' | 'created' | 'name' | 'unnamed' | 'count'`
- [ ] `SORT_CYCLE` und `sortLabel()` entsprechend ergänzen
- [ ] `sortedPersons()` — neue Zweige:
  ```typescript
  if (this.sortKey() === 'unnamed') {
    return list.sort((a, b) => {
      const aUnnamed = a.is_unknown || !a.name;
      const bUnnamed = b.is_unknown || !b.name;
      if (aUnnamed !== bUnnamed) { return aUnnamed ? -1 : 1; }
      return (a.name ?? '').localeCompare(b.name ?? '');
    });
  }
  if (this.sortKey() === 'count') {
    return list.sort((a, b) => b.count - a.count);
  }
  ```

### personen.html — Empty-States pro Gruppe/Filter

- [ ] Wenn `filteredPersons().length === 0` und Suche/Filter aktiv: „Keine Personen gefunden" statt der generellen Leerstate
- [ ] Unterscheidung von der bestehenden „Noch keine Personen erkannt"-Leerstate (die bleibt für den Fall ganz ohne Personen)

### Performance-Check

- [ ] Mit realistischer Personenzahl (Test-DB oder Produktions-Kopie) prüfen: Scroll-Ruckeln, Such-Tipp-Latenz
- [ ] Falls spürbar ruckelig: `computed()`-Ketten auf unnötige Neuberechnungen prüfen (z.B. `filteredPersons`/`sortedPersons` nicht mehrfach pro Render-Zyklus aufrufen)
- [ ] Nur wenn wirklich nötig: virtuelles Scrollen nachziehen (Vorlage: P20, falls im Repo vorhanden) — kein Vorgriff ohne Messung

---

## Doc-Updates

- [ ] Keine neuen Settings-Keys
- [ ] FINDINGS.md: Messergebnisse aus dem Performance-Check festhalten
