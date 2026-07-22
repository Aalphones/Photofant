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

1. `POST /knowledge/entities` akzeptiert `attributes` und legt sie an; der Entity-Owner bleibt
   `user`, jedes Merkmal behält den Owner aus dem Request (AK prüfbar: angelegte Entity hat
   `completeness > 0`, ein selbst eingetipptes Merkmal trägt Owner `user`, ein geschätztes
   `inferred`).
2. Die Interview-Zusammenfassung zeigt unter dem Profil-Text eine Sektion „Merkmale" mit je einer
   Zeile Label / Wert / Owner-Pill — „Selbst angegeben" bzw. „KI-Schätzung".
3. Liefert das Interview kein Merkmal, fehlt die Sektion komplett (keine leere Überschrift).
4. Über der Sektion steht eine Zeile „N von M Merkmalen gefüllt".
5. „Übernehmen" schreibt die Merkmale mit — nach dem Anlegen zeigt der Detail-Dialog dieselben
   Werte.
6. `uv run ruff check .`, `npm run lint`, `npm run build` grün.

## Checkliste

### Backend

- [ ] `AttributeDto` in `api/knowledge.py` bereitstellen (falls noch nicht vorhanden — sonst
      das bestehende wiederverwenden): `value: str`, `owner: str = "inferred"`,
      `confidence: float = 1.0`.
- [ ] `CreateEntityRequest.attributes: dict[str, AttributeDto] = {}` ergänzen.
- [ ] `to_entity()`: die Merkmale in `Entity.attributes` übertragen (`Attribute`-Objekte mit
      dem Owner aus dem DTO). Leere Werte überspringen.
- [ ] Prüfen, dass `create_entity(entity, owner)` die Attribute mitspeichert (der Vault
      serialisiert die ganze Entity) — falls nicht, dort ergänzen. **Nicht** den Entity-Owner
      auf die Merkmale durchschlagen lassen.
- [ ] Test: Create mit zwei Merkmalen → gespeicherte Entity hat beide, Owner `inferred`,
      Entity-Owner `user`, `completeness > 0`.

### Frontend — Model

- [ ] `InterviewAttributeDto` ergänzen: `{ label: string; value: string; owner: Owner; confidence: number }`.
- [ ] `KnowledgeInterviewSuggestion.attributes: Record<string, InterviewAttributeDto>`.
- [ ] `CreateEntityRequest.attributes?: Record<string, { value: string; owner: Owner; confidence: number }>`.

### Frontend — Interview-Dialog

- [ ] In `interview-dialog.ts` ein `computed` `extractedAttributes(): InterviewAttributeRow[]`
      (Typ mit `key`, `label`, `value`, `owner`) aus `result()?.suggestion?.attributes`,
      stabil sortiert nach Label.
- [ ] `computed` `attributeSummary()` für „N von M Merkmalen erkannt" — M ist die Anzahl der
      Merkmale des Ziel-Typs (`resolvedType()?.fields.length ?? 0`).
- [ ] `interview-dialog.html`: unter `<p class="iv-summary__body">` die Sektion einhängen,
      `@if (extractedAttributes().length > 0)`. Zeilenaufbau und Klassennamen analog
      `.kd-field-row` / `.kd-field-lbl` / `.kd-field-val` / `.kd-owner` aus dem Detail-Dialog,
      Präfix `iv-` statt `kd-`.
- [ ] `interview-dialog.scss`: die entsprechenden Regeln aus `knowledge-detail-dialog.scss`
      übernehmen (Owner-Pill-Farben inklusive).
- [ ] `onConfirm()`: `attributes` aus der Suggestion in den `CreateEntityRequest` übernehmen
      (Key → `{value, owner, confidence}`, ohne `label`).
- [ ] Erklärungs-Affordance: an der Sektions-Überschrift ein `title`-Tooltip „‚Selbst angegeben'
      hast du eingetippt, ‚KI-Schätzung' hat Gemma aus deinen Erzählungen abgeleitet. Beides
      kannst du später überschreiben."

### Docs

- [ ] `docs/routes.md`: `POST /knowledge/entities` um das Feld `attributes` ergänzen.
- [ ] `docs/models.md`: falls dort der Entity-Kontrakt beschrieben ist, `attributes` beim
      Anlegen erwähnen.

## Report-Back
