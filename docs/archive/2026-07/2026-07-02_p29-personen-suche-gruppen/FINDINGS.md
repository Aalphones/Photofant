# FINDINGS — P29 Personen-Suche/Filter/Gruppen

Unerwartete Erkenntnisse und Entscheidungen während der Umsetzung.

---

- [x] → Phase 5: `computed()`-Kette `filteredPersons → sortedPersons → personGroups` geprüft — Angular-Signals cachen automatisch, Mehrfach-Referenz im Template (Grid + Alphabet-Rail) verursacht keine doppelte Neuberechnung. Kein struktureller Perf-Fix nötig.
- [ ] → Phase 5 / Plan-Ende: Perf-Check mit realistischer Personenzahl (> 300) und echten Daten (Scroll-Ruckeln, Such-Tipp-Latenz) noch nicht durchgeführt — agentenlos ohne laufende App/Testdaten nicht simulierbar. Gehört in die Smoke-Checkliste am Plan-Ende.
