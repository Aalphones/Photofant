# Findings — P38 Wissen: Web-Recherche + neue Oberfläche

Getaggte Erkenntnisse aus der Umsetzung, die eine spätere Phase betreffen. Format:
`- [ ] → Phase N: <Erkenntnis>`. Wird von `mode-implementing` gepflegt.

- [ ] → Phase 3: `ddgs` 9.14.4 liefert die Keys `title` / `href` / `body` — genau die Form, die
  `search_web()` erwartet; keine Anpassung nötig. Ein Treffer ohne `href` wird verworfen, die
  Liste kann also kürzer sein als `max_results`. Der Job muss den Fall „0 Treffer" tragen
  (kein Fehler, sondern leere Fakten-Liste).
- [ ] → Phase 3: `set_attributes()` liefert `(Entity, geschriebene Keys, Meldungen zu
  übersprungenen)`. Die Übersprungen-Meldungen sind fertiger Klartext („'Geburtsort' bleibt
  unverändert — der Wert stammt von dir") und gehören unverändert in das `errors`-Feld der
  Apply-Antwort. Changelog schreibt `set_attributes` **nicht** — das macht die Route.
- [ ] → Phase 4: Merkmale liegen jetzt auch in der Cache-Spalte `knowledge_entities.attributes`
  (JSON, gleiche Form wie im Frontmatter, migration 0040). Die Aufgaben `missing_field` und
  `low_completeness` können daraus über **einen** Query erzeugt werden — kein Vault-Read je
  Entity nötig. `KnowledgeService._completeness_from_cache(row)` macht genau das schon.
- [ ] → Phase 6: `EntityDto.attributes` enthält nur die **gesetzten** Merkmale. Welche Felder
  ein Typ vorsieht (und damit welche als „fehlt"-Zeile erscheinen), steht in
  `GET /api/knowledge/domains` → `entity_types[].fields`. Die Detailansicht braucht beide
  Quellen, eine allein reicht nicht.
- [ ] → Smoke (Plan-Ende): ein **bestehender** Vault bekommt die neuen `fields:`-Blöcke nicht
  automatisch — die mitgelieferten Domänen werden nur einmalig gesät. Vor dem Smoke einmal von
  Hand `<vault>/domains/private.yaml` um den `fields:`-Block ergänzen (Vorlage:
  `backend/photofant/knowledge/domains/private.yaml`), sonst bleibt jeder Ring auf 0 %.
- [ ] → Phase 4: `autonomy_for()` fällt bei einem **unbekannten** Autonomie-Key auf `"ask"`
  zurück, nicht auf `"off"`. Für `discovery` greift das nie, weil `load_settings()` die
  Defaults tief einmischt — aber die Route muss trotzdem auf `!= "auto"` gaten (so geplant),
  nicht auf `== "off"`, sonst wäre `"ask"` versehentlich durchlässig.
