# Phase 4 — Routen, Guards und die drei neuen Aufgaben-Arten

**Komplexität:** standard (Routen folgen exakt dem Muster der bestehenden P27-Routen; die
Aufgaben-Erzeuger sind deterministisch, keine offenen Entscheidungen).
**Voraussetzung:** Phase 2 (Merkmale) und Phase 3 (Job liefert Vorschläge).

Diese Phase macht das Backend fertig: Recherche starten, bestätigte Fakten übernehmen, und die
drei Aufgaben-Arten erzeugen, die die Design-Übersicht in Phase 5 anzeigt.

## Kontext (lesen vor dem Start)
- `backend/photofant/api/knowledge_ai.py` — **die ganze Datei ist die Vorlage.** Besonders:
  `_is_private_domain` (Zeile 31), `AutonomyDto` (43), `get_autonomy` (115),
  `request_import_suggestion` (125 — gleicher Guard-Stil: 409 bei `off`, 422 bei privater
  Domäne), `accept_update_suggestion` (Vorbild für eine synchrone Übernahme-Route).
- `backend/photofant/knowledge/tasks.py` — `TaskKind` (Zeile 20-25), `TaskService.create_task`
  (58, **idempotent** über `kind` + `context`), `TaskStatus`.
- `backend/photofant/knowledge/service.py` — `_flag_if_incomplete` (Zeile 118) als Vorbild und
  als Einhängepunkt; `set_attributes` + `completeness_for` (neu aus Phase 2); `create_entity`,
  `create_relationship`, `search_entities`, `find_entity`.
- `backend/photofant/knowledge/changelog.py` — `ChangelogService.record(entity_id, field,
  old_value, new_value, reason, source, job_id)`.
- `backend/photofant/db/models.py` Zeile 27-34 — `Person` (`id`, `name: str | None`,
  `is_unknown`). Für den Namens-Abgleich zählen nur Personen mit `name is not None` und
  `is_unknown == False`.
- `backend/photofant/api/knowledge_tasks.py` — `TaskDto.from_task` (45), `_parse_kind` (70).
- `backend/photofant/jobs/recommendation_job.py` — `invalidate_recommendations(session,
  asset_ids)`; `backend/photofant/recommendation/context.py` — `assets_for_entity`. Beide nur
  relevant, wenn beim Übernehmen neue Beziehungen entstehen (Muster: `knowledge_patch_job.py`).
- `docs/routes.md` — Abschnitt zu den P27-KI-Routen (um Zeile 1091) als Format-Vorlage.

## Aufgabe 1 — Autonomie-DTO + Recherche-Route
`api/knowledge_ai.py`:

`AutonomyDto` um `discovery: str` erweitern, `get_autonomy()` um
`discovery=autonomy_for(Capability.KNOWLEDGE_DISCOVERY)`.

Neue Route `POST /discovery`:
```python
class DiscoveryRequest(BaseModel):
    """P38 — startet den KnowledgeDiscoveryJob. Das Ergebnis sind Vorschläge (ADR-031);
    geschrieben wird erst über /discovery/apply."""

    entity_id: str


class DiscoveryResponse(BaseModel):
    job_id: str
```
Guards, in dieser Reihenfolge:
1. `autonomy_for(Capability.KNOWLEDGE_DISCOVERY) != "auto"` → **409**,
   `"Web-Recherche ist in den Einstellungen deaktiviert"`.
2. leere `entity_id` → **422**, `"entity_id ist erforderlich"`.
3. Entity nicht gefunden → **404**.
4. `_is_private_domain(entity.domain)` → **422**,
   `"Private Entitäten werden nie web-recherchiert — nutze „Ergänzen (KI)" (webfrei)"`.

Dann `await enqueue_knowledge_discovery(body.entity_id)`, `job_id` zurück.

Kleiner neuer Helfer (die Entity wird für den Domänen-Guard gebraucht, `_is_private_domain`
nimmt nur einen Domänen-Namen):
```python
def _entity_for_guard(entity_id: str) -> Entity | None:
    """Lädt die Entity nur für den Privat-Domain-Guard — der Job lädt sie danach erneut
    (eigene DB-Session im Thread), doppeltes Lesen ist hier bewusst in Kauf genommen statt
    eine Session über die async-Grenze zu reichen."""
    from photofant.db.session import SessionLocal
    from photofant.knowledge.service import KnowledgeService

    with SessionLocal() as session:
        return KnowledgeService(session, open_vault()).find_entity(entity_id)
```

## Aufgabe 2 — Übernahme-Route (der Schreibweg)
Ebenfalls `api/knowledge_ai.py`, synchron (kein Job — es läuft kein Modell mehr):
```python
class DiscoveryFactDto(BaseModel):
    field: str
    label: str
    value: str
    source: str
    source_url: str
    confidence: float


class DiscoveryEntitySuggestionDto(BaseModel):
    title: str
    type: str
    relationship_type: str
    body: str


class DiscoveryApplyRequest(BaseModel):
    entity_id: str
    facts: list[DiscoveryFactDto] = []
    entity_suggestions: list[DiscoveryEntitySuggestionDto] = []


class DiscoveryApplyResponse(BaseModel):
    written_fields: list[str]
    created_entities: list[EntityRefDto]
    errors: list[str]
```

`POST /discovery/apply` — Ablauf:
1. **Dieselben Guards wie oben** (409 / 404 / 422 privat). Auch hier prüfen, nicht darauf
   vertrauen, dass der Aufrufer schon durch die Start-Route kam.
2. Fakten aufteilen: `field == "body"` → Beschreibung, alles andere → Merkmale.
3. **Beschreibung:** über `service.validate_patch` + `service.update_entity(entity_id,
   {"body": …, "sources": zusammengeführt}, Owner.WEB)`. `sources` = bestehende plus die
   `source_url`s der übernommenen Fakten, dedupliziert und sortiert. Validierungsfehler landen
   in `errors`, nicht als Exception.
4. **Merkmale:** `service.set_attributes(entity_id, {key: Attribute(value, Owner.WEB,
   confidence)}, Owner.WEB)` — ein Aufruf für alle. Die dritte Rückgabe (übersprungene Keys)
   fließt unverändert in `errors`. **Das ist der Punkt, an dem ein `user`-Merkmal geschützt
   wird** — das Frontend darf den Haken setzen, das Backend entscheidet.
5. **Vorgeschlagene Entitäten:** je Vorschlag
   - Typ/Beziehung gegen die Domäne prüfen (`has_entity_type`, `has_relationship_type`),
     sonst `errors` += `f"'{titel}': unbekannter Typ oder Beziehung, übersprungen"`.
   - Namensgleiche Entity suchen (`search_entities(titel, type=…, domain=…)`, Vergleich
     `title.strip().lower()`); gefunden → verwenden, sonst `create_entity` mit
     `id=f"{domain.folder_for(typ)}/{slugify(titel)}"`, `owner=Owner.WEB`.
     `EntityAlreadyExistsError`/`ValidationError` → `errors`, weiter.
   - Beziehung anlegen, wenn sie noch nicht existiert.
   - `assets_for_entity` für beide Seiten sammeln.
6. **Changelog:** je geschriebenem Feld/Merkmal ein `ChangelogService.record(...)` mit
   `reason=f"Web-Recherche, von dir bestätigt (Quelle: {source})"`, `source=Owner.WEB.value`,
   `job_id=None`. Ohne diesen Schritt ist „Warum geändert?" leer und die finale AK fällt durch.
7. Gesammelte Asset-IDs → `invalidate_recommendations`, dann `session.commit()`.
8. Nach dem Commit: `refresh_completeness_tasks(session, entity_id)` (Aufgabe 3) — die
   Übernahme kann eine „Feld fehlt"-Aufgabe erledigt haben.

## Aufgabe 3 — Neue Aufgaben-Arten
`knowledge/tasks.py`, `TaskKind` erweitern:
```python
    MISSING_FIELD = "missing_field"
    LOW_COMPLETENESS = "low_completeness"
    AUTO_LINK = "auto_link"
```

Neues Modul `backend/photofant/knowledge/task_rules.py` — die Erzeuger. Bewusst eigenes Modul:
`service.py` ist schon groß, und die Regeln hier sind reine Ableitungen ohne eigenen Zustand.

```python
LOW_COMPLETENESS_THRESHOLD = 0.34   # unter einem Drittel gefüllt = „kaum ausgefüllt"
AUTO_LINK_MIN_SCORE = 0.80          # darunter ist ein Namens-Treffer mehr Rauschen als Hilfe
```

**`refresh_completeness_tasks(session, entity_id)`** — nach jedem Schreiben auf einer Entity:
- Entity + Domäne laden, Vollständigkeit berechnen.
- Fehlende Merkmale (definiert, aber leer/nicht vorhanden) → falls mindestens eins:
  `create_task(MISSING_FIELD, {"entity_id": …, "title": …, "fields": [label, …]})`.
  Keine fehlenden mehr → offene `missing_field`-Aufgabe dieser Entity auf `resolved` setzen.
- Vollständigkeit unter dem Schwellwert **und** mindestens ein Merkmal definiert →
  `create_task(LOW_COMPLETENESS, {"entity_id": …, "title": …, "completeness": wert})`,
  sonst offene auflösen.
- `create_task` ist über `kind` + `context` idempotent — ändert sich die Feldliste, entsteht
  automatisch eine neue Aufgabe. Deshalb: **erst** die alten offenen dieser Entity auflösen,
  **dann** die neue anlegen, sonst stapeln sich Varianten.

**`refresh_auto_link_tasks(session)`** — Namens-Abgleich:
- Alle Entities ohne Person-Medien-Link laden, deren Domäne `private` ist (nur dort ergibt eine
  Zuordnung zu einer Foto-Person Sinn).
- Alle Personen mit `name is not None` und `is_unknown == False`, die noch keine verknüpfte
  Entity haben.
- Score über `difflib.SequenceMatcher(None, a, b).ratio()` auf normalisierten Namen
  (kleingeschrieben, Satzzeichen raus, Mehrfach-Leerzeichen zusammengezogen).
- Bester Treffer je Entity über `AUTO_LINK_MIN_SCORE` →
  `create_task(AUTO_LINK, {"entity_id": …, "title": …, "person_id": …, "person_name": …,
  "score": round(score, 2)})`.
- Aufgerufen: nach `create_entity`, nach dem Lösen einer Verknüpfung, und nach dem Anlegen/
  Umbenennen einer Person (`api/persons.py`). Kein Hintergrund-Lauf, kein Zeitplan.

Einhängepunkte im `KnowledgeService`: `_flag_if_incomplete` bleibt wie es ist (es deckt den
anderen Fall ab — Entity komplett ohne Inhalt); die neuen Aufrufe kommen daneben in
`create_entity` und in `set_attributes`/`update_entity`.

`api/knowledge_tasks.py` — `_parse_kind` deckt die neuen Werte automatisch ab, sobald sie im
Enum stehen. Nur prüfen, ob irgendwo eine harte Liste der Kinds steht (grep nach
`TaskKind.` in `api/`), und die mitziehen.

## Aufgabe 4 — Frontend-Modelle (nur Typen)
`frontend/src/app/models/job.model.ts`: `'knowledge_discovery'` in `JOB_KINDS` (nach
`'interview'`, vor `'recommendation'`).

`frontend/src/app/models/knowledge.model.ts`:
- `TASK_KINDS` um `'missing_field'`, `'low_completeness'`, `'auto_link'` erweitern.
- `AiAutonomyDto` += `discovery: AiAutonomyMode;` mit Kommentar, dass praktisch nur
  `'off'`/`'auto'` vorkommen.
- Die Discovery-Typen aus dem README-Kontrakt anlegen: `DiscoveryRequest`,
  `DiscoveryResponse`, `KnowledgeDiscoveryFact`, `KnowledgeDiscoveryEntitySuggestion`,
  `KnowledgeDiscoveryResult`, `DiscoveryApplyRequest`, `DiscoveryApplyResponse`.

`frontend/src/app/services/knowledge.service.ts`, nach `acceptUpdateSuggestion`:
```ts
  // P38 — startet die Web-Recherche. Das Job-Ergebnis sind Vorschläge, nichts ist
  // geschrieben; erst applyDiscovery schreibt (ADR-031).
  requestDiscovery(request: DiscoveryRequest): Observable<DiscoveryResponse> {
    return this.http.post<DiscoveryResponse>('/api/knowledge/ai/discovery', request);
  }

  applyDiscovery(request: DiscoveryApplyRequest): Observable<DiscoveryApplyResponse> {
    return this.http.post<DiscoveryApplyResponse>('/api/knowledge/ai/discovery/apply', request);
  }
```

## AK dieser Phase
- [ ] `GET /api/knowledge/ai/autonomy` liefert `discovery: "off"` im Auslieferungszustand.
- [ ] `POST /discovery` mit `discovery == "off"` → 409; mit privater Entity (nach Umstellen auf
      `"auto"`) → 422; mit öffentlicher Entity → 200 und der Job taucht im Job-Dock auf.
- [ ] `POST /discovery/apply` mit zwei Fakten schreibt beide als Merkmale mit `owner: web`; die
      Markdown-Datei zeigt sie im `attributes`-Block.
- [ ] Ein Fakt auf ein Merkmal, das `owner: user` trägt, wird **nicht** geschrieben und taucht
      in `errors` als Klartext-Meldung auf.
- [ ] „Warum geändert?" (`GET /api/knowledge/entities/{id}/changelog`) zeigt nach der Übernahme
      je geschriebenem Feld einen Eintrag mit der Quelle im Grund-Text.
- [ ] Eine Entity mit 5 definierten und 1 gefüllten Merkmal erzeugt sowohl eine
      „Feld fehlt"- als auch eine „kaum ausgefüllt"-Aufgabe; nach dem Füllen aller Merkmale ist
      keine der beiden mehr offen.
- [ ] Eine unverknüpfte private Entity „Noah B." und eine Person „Noah" erzeugen genau **eine**
      Verknüpfungs-Aufgabe mit einem Score über 0.8.
- [ ] `ruff` + `mypy` ohne neue Fehler, `npx tsc --noEmit` grün.

## Doc-Updates
- [ ] `docs/routes.md` — beide neuen Routen mit Guards (409/422/404) und Antwortform.
- [ ] `docs/models.md` — die drei neuen Aufgaben-Arten samt Context-Feldern.
- [ ] `docs/code-map.md` — `knowledge/task_rules.py` + die neuen Routen ergänzen.

## Report-Back
