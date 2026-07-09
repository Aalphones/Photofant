# FINDINGS — P23 Knowledge Wizard

> Format: `- [ ] → Phase N: <Erkenntnis>`. Mechanik: `mode-implementing`.

- [x] → Phase 3: `EntityWizardDialog` (`features/wissen/entity-wizard-dialog/`) hat bereits einen
  `prefill = input<Partial<CreateEntityRequest>>({})` für die Vorbelegung aus einer Aufgabe (Domäne/
  Typ/Titel werden daraus vorbelegt, wenn gesetzt). Zum Öffnen aus der Work-Queue einfach `prefill`
  mit dem Aufgaben-Kontext befüllen — kein Dialog-Umbau nötig. Nach `save`-Event (→ `createEntity`
  im `knowledge`-Store) auf `knowledgeSelectors.selectLastCreatedEntity` reagieren, um die Aufgabe
  aufzulösen (`POST /tasks/{id}/resolve`, noch zu ergänzen in `knowledge.service.ts`).
- [x] → Phase 3: `store/knowledge/` ist als EntityAdapter für **Domänen** aufgebaut (`selectId =
  domain.name`), nicht für Tasks. Für die Task-Liste braucht Phase 3 einen zweiten EntityAdapter
  im selben State-Interface (`KnowledgeState`) — Plan sagt „Slice aus Phase 2 wiederverwenden",
  das heißt: State/Actions/Reducer erweitern, nicht ersetzen.
