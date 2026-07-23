# Phase 4 — Web-Recherche: bevorzugte Quellen nutzen und Einträge bestätigen

**Rating:** standard

Zwei Dinge am selben Weg: Die Suche soll die für eine Domäne sinnvollen Quellen bevorzugen
(Schauspieler → IMDb, Wikipedia), und der Nutzer soll sehen, was angelegt wird, bevor es angelegt
wird.

## Teil A — Bevorzugte Quellen (Backend)

Heute baut der Job stumpf `"<Titel> <Typ>"` als Suchanfrage (`knowledge_discovery_job.py`
Zeile 298) und nimmt, was DuckDuckGo liefert. Mit Phase 1 kennt jede Domäne/jeder Typ ihre
bevorzugten Hosts.

**Vorgehen: zwei Durchläufe, nicht ein hartes Filter.** Ein `site:`-Filter allein kann leer
zurückkommen; dann stünde die Recherche ohne alles da. Also erst gezielt, dann auffüllen.

### AK Teil A

1. Gibt es bevorzugte Quellen, läuft zuerst eine Suche, die auf sie eingeschränkt ist
   (`<Titel> <Typ> (site:imdb.com OR site:wikipedia.org)`), danach die bisherige, unbeschränkte
   Suche zum Auffüllen.
2. Treffer werden zusammengeführt, nach URL entdoppelt, bevorzugte Quellen stehen **vorn**, und
   insgesamt bleibt es bei höchstens `MAX_SEARCH_RESULTS`.
3. Ohne bevorzugte Quellen verhält sich der Job exakt wie bisher (eine Suche, unverändert).
4. Liefert der eingeschränkte Durchlauf nichts, ist das kein Fehler — der unbeschränkte trägt.
5. Ein vom Nutzer eingegebener Hinweis wird weiterhin an **beide** Anfragen angehängt.
6. Private Domänen erreichen diesen Job unverändert nie (bestehender Guard, hier nur nicht brechen).

### Checkliste Teil A

- [x] In `_run_discovery` die Domäne laden (falls nicht schon vorhanden) und
      `domain.preferred_sources_for(entity.type)` holen.
- [x] Hilfsfunktion `_build_queries(entity, hint, preferred) -> list[str]`: bei leerem
      `preferred` genau eine Anfrage wie bisher; sonst zwei (eingeschränkt, dann offen).
- [x] Hilfsfunktion `_merge_results(primary, fallback, limit) -> list[WebSearchResult]`:
      Reihenfolge erhalten, nach `url` entdoppeln, auf `limit` kürzen.
- [x] `WebSearchError` des **eingeschränkten** Laufs abfangen und mit leerer Liste weitermachen
      (AK 4); der offene Lauf behält sein bisheriges Fehlerverhalten.
- [x] Tests: mit/ohne bevorzugte Quellen, Entdoppelung, Reihenfolge, Fehler im ersten Lauf.

## Teil B — Gefundene Einträge sichtbar bestätigen (Frontend)

`web-search-dialog.ts` Zeile 143 schickt beim Übernehmen
`entity_suggestions: this.searchResult()?.entity_suggestions ?? []` mit — **alle** von Gemma
vorgeschlagenen neuen Einträge, ungefiltert. Die Oberfläche zeigt nur die *Fakten* mit Checkboxen.
Neue Einträge landen damit im Vault, ohne dass der Nutzer sie je gesehen hat. Das widerspricht dem
Grundsatz des ganzen Wegs („Gemma schlägt vor, du bestätigst", ADR-031).

### Kontext — das musst du lesen

- `frontend/src/app/features/wissen/web-search-dialog/web-search-dialog.html` Zeilen 92-107 —
  **Referenz-Muster** für eine abhakbare Zeile (`.ws-fact-row`).
- `frontend/src/app/features/wissen/web-search-dialog/web-search-dialog.ts` — `isChecked`,
  `toggleFact`, `acceptedFacts`, `acceptedCount`, `applyState` (Zeile 135-160).
- `frontend/src/app/models/knowledge.model.ts` → `KnowledgeDiscoveryEntitySuggestion`
  (`title`, `type`, `relationship_type`, `body`), `DiscoveryApplyRequest`.
- `backend/photofant/jobs/knowledge_discovery_job.py` (Teil A), `inference/web_search.py`
- `docs/decisions/031-web-recherche-netzwerkzugriff.md`

### AK Teil B

1. Liefert die Recherche `entity_suggestions`, erscheint unter den Fakten eine zweite Sektion
   „Gefundene Verknüpfungen" mit je einer abhakbaren Zeile: Titel, darunter Typ und
   Beziehungstyp, plus Kurztext.
2. Haken sind vorbelegt **an** (wie bei den Fakten), jede Zeile ist abwählbar.
3. `applyDiscovery` erhält **ausschließlich** die angehakten Einträge.
4. Ein abgewählter Eintrag wird nicht angelegt (prüfbar: fehlt danach in der Wissen-Übersicht).
5. Der Primär-Button zählt beides: „N Einträge übernehmen".
6. Ohne `entity_suggestions` sieht der Dialog aus wie bisher (keine leere Sektion).
7. Die Quellen-Zeile eines Fakts zeigt weiterhin den Host — bevorzugte Quellen brauchen keine
   Sonderkennzeichnung.

### Checkliste Teil B

- [x] Zweiter Auswahl-Zustand analog zu den Fakten: `checkedEntities`, `isEntityChecked(index)`,
      `toggleEntity(index)` — **Muster von `isChecked`/`toggleFact` übernehmen**.
- [x] Vorbelegung: beim Eintreffen des Ergebnisses alle Indizes angehakt, gleicher Mechanismus
      wie bei den Fakten.
- [x] `acceptedEntitySuggestions()` als `computed`.
- [x] Zeile 143: `entity_suggestions: this.acceptedEntitySuggestions()`. **Das ist der Fix.**
- [x] `acceptedCount()` um die angehakten Verknüpfungen erweitern (steuert Button-Label und
      `primaryDisabled`).
- [x] Button-Label „{{ acceptedCount() }} Einträge übernehmen".
- [x] Template: neue Sektion nach der Fakten-Schleife,
      `@if ((searchResult()?.entity_suggestions ?? []).length > 0)`, Überschrift im Stil
      `.ws-summary-label`, Zeilen im Stil `.ws-fact-row`.
- [x] Erklärungs-Affordance: `title`-Tooltip an der Überschrift — „Neue Einträge, die Gemma
      zusätzlich gefunden hat. Nur Angehaktes wird angelegt."
- [x] `.scss` um die Beziehungstyp-Zeile ergänzt (`.ws-entity-body`), bestehende Fakten-Klassen
      wiederverwendet (`.ws-fact-row`, `.ws-fact-body`, `.ws-fact-field`, `.ws-summary-label`).

## Docs

- [x] `docs/models.md`: bevorzugte Quellen sind seit Phase 1 dokumentiert (Zeile ~530), inkl.
      der Private-Domänen-Ausnahme, die der Web-Recherche-Pfad hier unverändert respektiert —
      kein weiterer Eintrag nötig (Verweis genügt, s. Plan-Auflage).

## Report-Back

**Konfidenz-Check (README-Punkt 2) aufgelöst:** Live-Anfrage `"Tatiana Maslany Actor
(site:imdb.com OR site:wikipedia.org)"` gegen `search_web` gefahren — alle 8 Treffer kamen
ausschließlich von `imdb.com`/`wikipedia.org`. `ddgs` nimmt den `site:`-OR-Filter zuverlässig
an, kein Rückfallweg nötig.

**Gefundener und mitgefixter Bug (nicht Teil des ursprünglichen Auftrags, aber in derselben
Stelle, die Teil B ohnehin anfassen musste):** `acceptedCount()` zählte bisher
`Object.values(this.checked())` — ein Record, das erst durch Klicks befüllt wird. Ungeklickte
Zeilen sind visuell angehakt (`isChecked()` fällt auf `true` zurück), zählten aber nirgends mit.
Ergebnis: der „Fakten übernehmen"-Button blieb bis zum ersten Klick auf 0 stehen und war
disabled — ein Nutzer, der alle Vorschläge unverändert übernehmen wollte, kam nie durch. Fix:
`acceptedCount()` leitet sich jetzt direkt aus `isChecked()`/`isEntityChecked()` ab (Default
`true` korrekt mitgezählt) statt aus dem rohen Toggle-Record. Betrifft auch die neue
Verknüpfungs-Sektion — ohne den Fix wäre dort derselbe Fehler neu eingebaut worden.

Teil A: zwei Suchdurchläufe (eingeschränkt → offen), Merge dedupliziert nach URL und behält
bevorzugte Quellen vorn. Ohne `preferred_sources` unverändert eine Anfrage (AK 3 geprüft per
Unit-Test). 6 neue Backend-Tests (2 Integration über `_run_discovery`, 4 reine Query-/Merge-Unit-Tests
für Teil A) + Handling für Teil B — alle grün, `ruff`/`mypy` sauber.

Teil B: zweite abhakbare Sektion „Gefundene Verknüpfungen" nach den Fakten, gleiches
Vorbelegungs-/Toggle-Muster, eigener `computed` für die Übernahme-Filterung. `entity_suggestions`
gehen jetzt gefiltert statt ungefiltert in `applyDiscovery` — das war der eigentliche Fix aus
dem Plan (Zeile 143 alt). `npm run lint` (tsc --noEmit) und `npm run build` grün.
