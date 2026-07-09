# FINDINGS — P24 Photofant-Integration

> Format: `- [ ] → Phase N: <Erkenntnis>`. Mechanik: `mode-implementing`.

## Phase 1

- [x] → Phase 1: `KnowledgeService.link_media` existiert nicht (Plan-Kontrakt unterstellt es
  aus P22). Real gibt es nur den generischen `update_entity(patch={"media_links": …})`-Pfad.
  Gelöst: `link_media`/`unlink_media` als dünne, idempotente Methoden neu gebaut (Muster wie
  `create_relationship`/`remove_relationship`), kein `update_entity`-Umweg.
- [x] → Phase 1: Schleifenschutz-Infrastruktur (`ParentJobId`/`Depth` auf `JobStatus`,
  `jobs.maxDepth`) existiert nicht — P22 hat sie nie gebaut, obwohl der Plan-Text sie als
  vorhanden unterstellt. `KnowledgeLookupJob` ist strukturell ein Sackgassen-Job (löst nie
  einen Folge-Job aus); der bestehende `TaskService`-Dedup reicht als Schutz. Bewusst kein
  Nachbau (YAGNI, mit Nutzer abgestimmt) → **ADR-014**. `ADR-011` war für „intelligente Jobs"
  reserviert, ist inzwischen aber `011-galerie-virtual-scroll.md` — nächste freie Nummer war
  014 (012/013/015–025 bereits vergeben).
- [x] → Phase 1: `knowledge.autoLookup` (Plan-Notation) existierte nicht; als `knowledge.auto_lookup`
  angelegt (Snake_Case passend zu den übrigen `settings.py`-Keys), Default `true`.
- [x] → Phase 2: Task-Context trägt jetzt `{"ref": <Personenname>, "person_id": <id>}` statt nur
  `{"ref": …}` — die Wizard-Verdrahtung („Wissen anlegen" → Task resolven) kann darüber die
  passende `NEW_PERSON`-Aufgabe eindeutig der Person zuordnen, auch bei Namensgleichheit.
  Eingearbeitet: `Personen.newPersonTaskByPersonId` liest `context.person_id` direkt.

## Phase 2

- [ ] → Phase 3: Backend `PersonDto.linked_entity` (`EntityRefDto`, gebaut in Phase 1) existiert
  bereits und wird von `GET /api/persons` schon befüllt — das Frontend-`PersonDto`-Model
  (`models/person.model.ts`) hat das Feld aber noch **nicht** nachgezogen (war außerhalb von
  Phase 2s Scope). Phase 3 muss es dort + in `PersonService` ergänzen, bevor der Entity-Chip
  auf Personen-Karte/Asset-Detail angezeigt werden kann.
