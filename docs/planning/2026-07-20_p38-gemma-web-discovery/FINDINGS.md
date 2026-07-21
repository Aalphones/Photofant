# Findings — P38 Wissen: Web-Recherche + neue Oberfläche

Getaggte Erkenntnisse aus der Umsetzung, die eine spätere Phase betreffen. Format:
`- [ ] → Phase N: <Erkenntnis>`. Wird von `mode-implementing` gepflegt.

- [x] → Phase 3: `ddgs` 9.14.4 liefert die Keys `title` / `href` / `body` — genau die Form, die
  `search_web()` erwartet; keine Anpassung nötig. Ein Treffer ohne `href` wird verworfen, die
  Liste kann also kürzer sein als `max_results`. Der Job muss den Fall „0 Treffer" tragen
  (kein Fehler, sondern leere Fakten-Liste). Eingearbeitet: `_build_user_prompt` zeigt
  `"(keine Suchergebnisse)"`, der Parser degradiert auf ein leeres `DiscoveryOutput`.
- [x] → Phase 4 (Tag korrigiert, war fälschlich Phase 3 — der Job selbst schreibt nichts):
  `set_attributes()` liefert `(Entity, geschriebene Keys, Meldungen zu übersprungenen)`. Die
  Übersprungen-Meldungen sind fertiger Klartext („'Geburtsort' bleibt unverändert — der Wert
  stammt von dir") und gehören unverändert in das `errors`-Feld der Apply-Antwort. Changelog
  schreibt `set_attributes` **nicht** — das macht die Route.
  Eingearbeitet: `apply_discovery` reicht `skipped_messages` unverändert in `errors`, schreibt
  Changelog selbst je Feld.
- [x] → Phase 4: Neue Fehlerklasse `PrivateDomainError` (`knowledge/service.py`, neben
  `EntityNotFoundError`) — die Discovery-Route muss sie zu 422 abfangen, analog zum
  bestehenden `_is_private_domain`-Guard in `api/knowledge_ai.py`.
  Präzisiert beim Einarbeiten: `PrivateDomainError` fliegt nur im Job selbst (Verteidigung in
  der Tiefe bei direktem Job-Aufruf) — die Routen prüfen `domain.private` synchron **vor** dem
  Enqueue/Schreiben und geben 422 direkt zurück, kein Catch nötig.
- [x] → Phase 4 / User-Entscheidung: Domäne „Personen" (`personen.yaml`, echte private
  Kontakte wie `Person/anna-lieb`) trägt **kein** `private: true` — anders als die separate
  Domäne „Private". Vor dem Freischalten der Route klären, ob das gewollt ist (siehe
  Report-Back Phase 3).
  Entschieden (User, vor Phase-4-Start): ja, `private: true` setzen — echte Kontakte bleiben
  von der Web-Recherche ausgenommen. Umgesetzt.
- [x] → Phase 4: Merkmale liegen jetzt auch in der Cache-Spalte `knowledge_entities.attributes`
  (JSON, gleiche Form wie im Frontmatter, migration 0040). Die Aufgaben `missing_field` und
  `low_completeness` können daraus über **einen** Query erzeugt werden — kein Vault-Read je
  Entity nötig. `KnowledgeService._completeness_from_cache(row)` macht genau das schon.
  Bewusst anders gelöst: `refresh_completeness_tasks()` läuft als Hook direkt nach jedem
  Schreiben auf der **einen** gerade geschriebenen Entity (Plan-Vorgabe „nach jedem Schreiben"),
  kein Bulk-Scan über den Cache nötig — der Vault-Read passiert ohnehin schon für den Schreibpfad
  selbst. Der Cache-Query-Ansatz bleibt der richtige Weg, falls später ein Bulk-Backfill für
  Bestandsdaten gebraucht wird (z.B. Reconcile-Job).
- [ ] → Phase 6: `EntityDto.attributes` enthält nur die **gesetzten** Merkmale. Welche Felder
  ein Typ vorsieht (und damit welche als „fehlt"-Zeile erscheinen), steht in
  `GET /api/knowledge/domains` → `entity_types[].fields`. Die Detailansicht braucht beide
  Quellen, eine allein reicht nicht.
- [ ] → Phase 6: `EntityDto` (und `EntityRefDto`) trägt **kein** `updated_at`/`created_at`-Feld —
  verifiziert beim Bau der Phase-5-Sektion „Nicht verknüpfte Notizen", die laut Plan
  „geändert am {Datum}" zeigen sollte und das mangels Datenquelle weglassen musste (nur „{N} %"
  angezeigt). Phase 6, Aufgabe „Kopf" verlangt denselben Text
  („{N} % vollständig · {Domäne} · aktualisiert am {Datum}") — ohne Backend-Zusatzfeld (Vault-
  Datei-mtime oder ein neuer Zeitstempel in `Entity`) lässt sich das nicht ehrlich befüllen.
  Vor Phase 6 entscheiden: Datum weglassen (wie hier), oder kleinen Backend-Zusatz nachziehen
  (`Entity.updated_at` aus Datei-mtime, kein Kontrakt-Bruch, additive Erweiterung).
- [x] → Phase 5: `EntityRefDto` (`person.linked_entity`) trägt keine Domäne — für die
  Personen-Karten-Meta-Zeile „{N} % · {Domäne}" über `entityDomainById` in `wissen.ts` aus der
  vollständigen `entities()`-Liste aufgelöst (kein neuer Endpunkt). Für Phase 6/8 nicht relevant:
  beide arbeiten auf vollen `EntityDto`/`LoreDto`-Objekten, die `domain` direkt tragen.
- [ ] → Smoke (Plan-Ende): ein **bestehender** Vault bekommt die neuen `fields:`-Blöcke nicht
  automatisch — die mitgelieferten Domänen werden nur einmalig gesät. Vor dem Smoke einmal von
  Hand `<vault>/domains/private.yaml` um den `fields:`-Block ergänzen (Vorlage:
  `backend/photofant/knowledge/domains/private.yaml`), sonst bleibt jeder Ring auf 0 %.
- [x] → Phase 4: `autonomy_for()` fällt bei einem **unbekannten** Autonomie-Key auf `"ask"`
  zurück, nicht auf `"off"`. Für `discovery` greift das nie, weil `load_settings()` die
  Defaults tief einmischt — aber die Route muss trotzdem auf `!= "auto"` gaten (so geplant),
  nicht auf `== "off"`, sonst wäre `"ask"` versehentlich durchlässig.
  Eingearbeitet: beide Routen gaten auf `!= "auto"`, nicht auf `== "off"`.
