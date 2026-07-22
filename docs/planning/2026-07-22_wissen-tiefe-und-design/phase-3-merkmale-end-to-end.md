# Phase 3 — Merkmale speichern und im Wizard zeigen

**Rating:** standard (Kontrakt steht in der README, Muster im Bestand vorhanden)

Vertikale Scheibe: Backend nimmt Merkmale beim Anlegen entgegen, das Interview-Ergebnis zeigt
sie, und die Bestätigung schreibt sie mit. Ohne diese Phase liefert Phase 2 Merkmale, die
niemand sieht und die niemand speichert.

**Zwei Herkünfte, sichtbar getrennt:** Ein Merkmal kommt entweder aus einem Eingabefeld des
Nutzers (Owner `user` → Pill „Selbst angegeben") oder aus Gemmas Vorschlag für ein leer
gelassenes Feld (Owner `inferred` → Pill „KI-Schätzung"). Der Unterschied muss in der
Zusammenfassung erkennbar sein — sonst weiß der Nutzer nicht, was er gerade bestätigt.

## Kontext — das musst du lesen

- README dieses Plans, **Kontrakt-Sektionen 1 und 2**.
- `backend/photofant/api/knowledge.py` ab Zeile 210 (`CreateEntityRequest`, `to_entity`) und der
  zugehörige POST-Endpunkt.
- `backend/photofant/knowledge/service.py` → `create_entity` (Zeile 126).
- `backend/photofant/knowledge/schema.py` → `Attribute`, `Owner`.
- `frontend/src/app/models/knowledge.model.ts` → `KnowledgeInterviewSuggestion`,
  `CreateEntityRequest`, `AttributeDto`, `Owner`.
- `frontend/src/app/features/wissen/interview-dialog/interview-dialog.html` + `.ts` + `.scss`.
- `frontend/src/app/features/wissen/knowledge-detail-dialog/knowledge-detail-dialog.html`
  Zeilen 159-172 — **das ist das Referenz-Muster** für eine Merkmals-Zeile (Label / Wert /
  Owner-Pill). Nachbauen, nicht neu erfinden. Die Pill-Klassen stehen in
  `knowledge-detail-dialog.scss` (`.kd-owner--inferred` u.a.).
- `docs/conventions/angular.md`, `docs/conventions/typescript.md`, `docs/conventions/python.md`

**Design-Deckung:** Für „Merkmale in der Interview-Zusammenfassung" gibt es **kein** Mockup —
das Design zeigt dort nur den Fließtext. Entscheidung (mit dem Plan freigegeben): Wir übernehmen
1:1 das designte Merkmals-Zeilen-Muster aus dem Detail-Dialog, damit dieselbe Information überall
gleich aussieht. Kein eigener Entwurf.

## AK dieser Phase

1. [x] `POST /knowledge/entities` akzeptiert `attributes` und legt sie an; der Entity-Owner bleibt
   `user`, jedes Merkmal behält den Owner aus dem Request (AK prüfbar: angelegte Entity hat
   `completeness > 0`, ein selbst eingetipptes Merkmal trägt Owner `user`, ein geschätztes
   `inferred`). Test: `test_create_entity_persists_attributes_with_own_owner`.
2. [x] Die Interview-Zusammenfassung zeigt unter dem Profil-Text eine Sektion „Merkmale" mit je
   einer Zeile Label / Wert / Owner-Pill — „Selbst angegeben" bzw. „KI-Schätzung".
3. [x] Liefert das Interview kein Merkmal, fehlt die Sektion komplett (keine leere Überschrift) —
   `@if (extractedAttributes().length > 0)`.
4. [x] Über der Sektion steht eine Zeile „N von M Merkmalen gefüllt".
5. [x] „Übernehmen" schreibt die Merkmale mit — nach dem Anlegen zeigt der Detail-Dialog dieselben
   Werte (Backend-Pfad geprüft per Test; Detail-Dialog liest ohnehin live aus `EntityDto.attributes`).
6. [x] `uv run ruff check .`, `npm run lint`, `npm run build` grün.

## Checkliste

### Backend

- [x] `AttributeDto` in `api/knowledge.py` bereitstellen (falls noch nicht vorhanden — sonst
      das bestehende wiederverwenden): `value: str`, `owner: str = "inferred"`,
      `confidence: float = 1.0`. War schon da (P38 Phase 2), nur die zwei Defaults ergänzt.
- [x] `CreateEntityRequest.attributes: dict[str, AttributeDto] = {}` ergänzen.
- [x] `to_entity()`: die Merkmale in `Entity.attributes` übertragen (`Attribute`-Objekte mit
      dem Owner aus dem DTO). Leere Werte überspringen.
- [x] Geprüft: `create_entity(entity, owner)` speichert die Attribute bereits mit
      (`Vault.save_entity` → `serialize_entity` → `attributes_to_mapping`, kam mit P38 Phase 2)
      — keine Ergänzung nötig. Entity-Owner schlägt nicht durch (`to_entity()` übernimmt den
      Owner pro Merkmal aus dem DTO, nicht den Request-`owner`).
- [x] Test: Create mit zwei Merkmalen → gespeicherte Entity hat beide, ein Owner `user`, ein
      `inferred`, Entity-Owner `user`, `completeness > 0`.

### Frontend — Model

- [x] `InterviewAttributeDto` ergänzen: `{ label: string; value: string; owner: Owner; confidence: number }`.
- [x] `KnowledgeInterviewSuggestion.attributes: Record<string, InterviewAttributeDto>`.
- [x] `CreateEntityRequest.attributes?: Record<string, { value: string; owner: Owner; confidence: number }>`.

### Frontend — Interview-Dialog

- [x] In `interview-dialog.ts` ein `computed` `extractedAttributes(): InterviewAttributeRow[]`
      (Typ mit `key`, `label`, `value`, `owner`) aus `result()?.suggestion?.attributes`,
      stabil sortiert nach Label.
- [x] `computed` `attributeSummary()` für „N von M Merkmalen gefüllt" — M ist die Anzahl der
      Merkmale des Ziel-Typs (`resolvedType()?.fields.length ?? 0`).
- [x] `interview-dialog.html`: unter `<p class="iv-summary__body">` die Sektion einhängen,
      `@if (extractedAttributes().length > 0)`. Zeilenaufbau und Klassennamen analog
      `.kd-field-row` / `.kd-field-lbl` / `.kd-field-val` / `.kd-owner` aus dem Detail-Dialog,
      Präfix `iv-` statt `kd-`.
- [x] `interview-dialog.scss`: die entsprechenden Regeln aus `knowledge-detail-dialog.scss`
      übernehmen (Owner-Pill-Farben inklusive) — nur zwei Owner-Fälle (`user`/`inferred`)
      statt vier, eigene `ivOwnerLabel()`/`ivOwnerClass()` statt der Detail-Dialog-Variante
      (dort heißt `user` „Manuell", hier bewusst „Selbst angegeben").
- [x] `onConfirm()`: `attributes` aus der Suggestion in den `CreateEntityRequest` übernehmen
      (Key → `{value, owner, confidence}`, ohne `label`) — nur im Anlege-Zweig (neue Entity).
      Der Update-Zweig (Interview auf eine bereits verknüpfte Person mit bestehender Notiz)
      patcht weiterhin nur `title`/`body` — siehe Report-Back.
- [x] Erklärungs-Affordance: an der Sektions-Überschrift ein `title`-Tooltip „‚Selbst angegeben'
      hast du eingetippt, ‚KI-Schätzung' hat Gemma aus deinen Erzählungen abgeleitet. Beides
      kannst du später überschreiben."

### Docs

- [x] `docs/routes.md`: `POST /knowledge/entities` um das Feld `attributes` ergänzen.
- [x] `docs/models.md`: Entity-Kontrakt ist schon schema-generisch beschrieben (Frontmatter-
      Block, DB-Spalte) und endpoint-neutral — keine Änderung nötig, Duplikat vermieden.

## Report-Back

**Backend:** `CreateEntityRequest.attributes` + `to_entity()`-Mapping in
`backend/photofant/api/knowledge.py`; ein neuer API-Test. Serialisierung/Completeness-Rechnung
gab es schon aus P38 Phase 2 — nichts davon musste angefasst werden.

**Frontend:** `InterviewAttributeDto` + `attributes`-Feld auf `CreateEntityRequest`/
`KnowledgeInterviewSuggestion` im Model; im Interview-Dialog eine neue Merkmale-Sektion in der
Zusammenfassung (eigene Owner-Pills, zwei Fälle statt vier) plus die Übernahme in
`onConfirm()`.

**🟡 Bewusst nicht mitgefixt — dem User zur Entscheidung vorgelegt:** Läuft das Interview über
eine Person, die schon eine Notiz hat (`target.entityId` gesetzt), geht die Bestätigung über
den `UpdateEntityRequest`-Zweig, nicht `CreateEntityRequest`. Dieser Zweig schreibt bisher nur
`title`/`body` — der Kontrakt dieser Phase (README Sektion 2) hat ausdrücklich nur das Anlegen
erweitert, `PATCH .../entities/{id}` kennt `attributes` serverseitig noch gar nicht als
patchbares Feld (`PATCHABLE_FIELDS` in `service.py`). Wer eine bereits verknüpfte Person erneut
interviewt, bekommt die Merkmale also aktuell **nicht** gespeichert, nur bei neu angelegten
Notizen. War nicht Teil des Kontrakts dieser Phase — bewusst ausgelassen, kein FINDINGS-Eintrag,
weil keine der verbleibenden Phasen das Thema trägt. Falls gewünscht, ist es ein kleiner
Folgeauftrag (attributes zu `PATCHABLE_FIELDS` + `set_attributes`-Aufruf statt Direkt-Patch).
