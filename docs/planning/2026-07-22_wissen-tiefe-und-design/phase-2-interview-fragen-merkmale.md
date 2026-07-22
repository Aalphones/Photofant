# Phase 2 — Interview: Fragen aus der Domäne, Antworten feldgenau

**Rating:** heikel (neue Prompt-Struktur + Parsing; die Fragen-Herkunft ändert sich grundlegend)

## Der Kern dieser Phase

Bisher: fünf feste Fragen im Frontend, Gemma erzeugt daraus einen Absatz, kein Merkmal wird
gefüllt. Künftig zweigleisig:

- **Gefragte Merkmale zählen direkt.** Für jedes Merkmal mit `question` (Phase 1) gibt es ein
  eigenes Eingabefeld. Was der Nutzer dort hineinschreibt, wird **wörtlich** übernommen — Owner
  `user`, kein Modell dazwischen, keine Halluzination möglich.
- **Erzähl-Antworten werden zum Profiltext.** Die drei offenen Fragen speisen wie bisher den
  Absatz, den Gemma schreibt.
- **Optionaler Bonus:** Für Merkmale, die der Nutzer **leer gelassen** hat, darf Gemma aus den
  Erzähl-Antworten einen Wert vorschlagen — Owner `inferred`, klar als KI-Schätzung erkennbar.
  Ein vom Nutzer gefülltes Merkmal wird davon nie angefasst.

Das verlagert das Gewicht vom Raten aufs Fragen. Der riskante Teil bleibt klein und ist optional.

## Kontext — das musst du lesen

- Phase 1 dieses Plans (die Domänen-Schlüssel `question` und `questions_for`).
- README, **Kontrakt-Sektion 1**.
- `backend/photofant/jobs/interview_job.py` — der ganze Job.
- `backend/photofant/inference/prompts/interview.md` — der System-Prompt.
- `backend/photofant/knowledge/schema.py` — `Entity`, `Attribute`, `Owner`.
- `backend/photofant/api/knowledge_ai.py` Zeile 214-238 — die auslösende Route und
  `InterviewAnswer`.
- `frontend/src/app/features/wissen/interview-dialog/interview-dialog.ts` — `INTERVIEW_QUESTIONS`
  (Zeile 26-32), `stepIndex`, `answers`, `submit()`, `resolvedType()`.
- `frontend/src/app/features/wissen/interview-dialog/interview-dialog.html`
- `docs/conventions/python.md`, `docs/conventions/angular.md`

**Chesterton's Fence:** Der Job ist heute absichtlich prosa-only — der Docstring nennt den Grund
(Konzept-ADR-009: „nur zusammenfassen, nie Fakten erfinden"). Diese Regel wird **nicht** gelöscht,
sondern präzisiert: Was der Nutzer selbst eingetippt hat, ist kein erfundener Fakt. Nur der
optionale Bonus-Pfad ist Modell-Interpretation, und der ist als solcher markiert.

## Fragen-Aufbau im Wizard

| Schritt | Inhalt |
|---|---|
| 0 | Personen-Wahl bzw. Bestätigungszeile (unverändert) |
| 1-3 | Die drei Erzähl-Fragen, je eine pro Schritt (unverändert im Stil) |
| 4 | **„Eckdaten"** — ein Schritt, darin je Merkmal mit Frage ein beschriftetes Eingabefeld |
| 5 | Zusammenfassung (Phase 3) |

Die drei Erzähl-Fragen (fest im Frontend, sie gehören zu keinem Merkmal):

1. `Was schätzt du an {name} am meisten?`
2. `Gibt es eine Geschichte oder ein Erlebnis, das {name} gut beschreibt?`
3. `Sonst noch etwas Wichtiges, das man wissen sollte?`

Die beiden alten Fragen zu Vorlieben und Beziehung **entfallen** — sie sind jetzt Merkmals-Fragen
aus der Domäne und würden sich sonst doppeln.

## AK dieser Phase

1. Die Merkmals-Fragen kommen aus der Domäne (`questions_for` des aufgelösten Typs), nicht aus
   einer Frontend-Konstante. Eine Domäne ohne Merkmals-Fragen zeigt Schritt 4 nicht.
2. `{name}` ist in jeder angezeigten Frage durch den Namen ersetzt.
3. Schritt 4 zeigt je Merkmal ein Feld mit der Frage als Beschriftung; alle sind optional.
4. `InterviewAnswer` trägt ein optionales `field_key`; Antworten aus Schritt 4 tragen es,
   Erzähl-Antworten nicht.
5. Ein Merkmal mit nicht-leerer Nutzer-Antwort landet **wörtlich** im Ergebnis, Owner `user`,
   Confidence 1.0 — unverändert durch das Modell.
6. Gemma darf nur Merkmale vorschlagen, die (a) in `fields_for` stehen und (b) vom Nutzer leer
   gelassen wurden. Diese tragen Owner `inferred`.
7. Liefert das Modell kein gültiges JSON, ist das Ergebnis trotzdem gültig: kompletter Text wird
   `body`, die **gefragten Merkmale bleiben erhalten** (sie hängen nicht am Modell). Kein Job-Fehler.
8. Ein Interview ganz ohne Antworten läuft durch und erzeugt ein Ergebnis ohne Merkmale.
9. `uv run ruff check .`, `npm run lint`, `npm run build` grün, neue Tests grün.

## Checkliste

### Backend — Kontrakt

- [ ] `InterviewAnswer` (Job **und** API-DTO in `knowledge_ai.py`) um `field_key: str | None = None`
      erweitern.

### Backend — Prompt

- [ ] `interview.md` auf JSON-Ausgabe umstellen: `body` (String) und `attributes`
      (Key → `{"value": String, "confidence": 0..1}`).
- [ ] Regeln im Prompt: nur die im Nutzer-Turn als „noch offen" gelisteten Keys verwenden; ein
      Merkmal nur setzen, wenn es eindeutig aus den Erzähl-Antworten hervorgeht; im Zweifel
      weglassen; nichts aus Weltwissen; kein Web.
- [ ] Prompt-`version` hochziehen (bestehendes Dateiformat beibehalten).

### Backend — Job

- [ ] In `_run_interview` `vault.load_domain(...)` **vor** den `generate()`-Aufruf ziehen (steht
      heute danach) — die Feld-Definitionen werden für den Prompt gebraucht.
- [ ] Antworten aufteilen: `answered_fields` (mit `field_key`, nicht-leer, Key in `fields_for`)
      und `narrative` (ohne `field_key`). Unbekannte `field_key` verwerfen.
- [ ] `_build_user_prompt(title, narrative, open_fields)`: Protokoll der Erzähl-Antworten +
      Liste der **noch offenen** Merkmale als `- <key> (<label>)`. Ist nichts offen, den
      Merkmals-Block weglassen.
- [ ] Neue Funktion `_parse_interview_output(raw, allowed) -> tuple[str, dict[str, Attribute]]`:
      - Code-Fence (```json … ```) abstreifen, `json.loads`.
      - Bei `JSONDecodeError`, Nicht-Dict oder fehlendem/leerem `body` → `(raw.strip(), {})`.
      - `attributes` filtern: Key nicht in `allowed` → raus; Wert kein String oder leer → raus;
        `confidence` fehlt/ungültig → `0.5`, sonst auf `0.0..1.0` klemmen.
      - Ergebnis-Attribute mit `owner=Owner.INFERRED`.
- [ ] Merkmale zusammenführen: erst die gefragten (`Owner.USER`, Confidence 1.0, Wert
      `.strip()`), dann die vom Modell vorgeschlagenen — **nur** für Keys, die noch nicht belegt
      sind (AK 6). Die gefragten gewinnen immer.
- [ ] `attributes` in den `Entity`-Kandidaten setzen, damit der P22-Validator sie mitprüft.
- [ ] Ergebnis-Payload `suggestion.attributes` nach README-Kontrakt 1 (Key →
      `{label, value, owner, confidence}`), Label aus `fields_for`.
- [ ] Modul-Docstring nachziehen (Chesterton's Fence oben).

### Frontend — Interview-Dialog

- [ ] `INTERVIEW_QUESTIONS` auf die drei Erzähl-Fragen kürzen, mit `{name}`-Platzhalter.
- [ ] `computed` `fieldQuestions()`: Merkmale des aufgelösten Typs mit gesetzter `question`,
      `{name}` ersetzt.
- [ ] `computed` `hasFieldStep()` — steuert, ob Schritt 4 existiert.
- [ ] Zweiter Antwort-Speicher `fieldAnswers = signal<Record<string, string>>({})`, Key =
      Merkmals-Key.
- [ ] Schrittzählung anpassen: Gesamtzahl = 3 (+1 wenn `hasFieldStep()`); der Fortschrittstext
      „Frage X von N" bleibt, Schritt 4 zeigt „Eckdaten" als Titel statt einer Nummer-Frage.
- [ ] Template: neuer Block für Schritt 4 — je Merkmal ein `<label>` mit der Frage und ein
      einzeiliges `<input>` (kein Textarea; das sind kurze Werte). Alle optional, Hinweiszeile
      „Alles freiwillig — leer lassen ist in Ordnung."
- [ ] `submit()`: `answers` bauen aus den drei Erzähl-Antworten (ohne `field_key`) **plus** je
      Merkmal mit nicht-leerem Wert ein Eintrag `{question, answer, field_key}`.

### Tests

- [ ] `_parse_interview_output`: gültiges JSON, kaputtes JSON (Fallback), unbekannter Key,
      leerer Wert, Confidence-Klemmung.
- [ ] Zusammenführung: gefragtes Merkmal schlägt Modell-Vorschlag desselben Keys (AK 6).
- [ ] Gefragte Merkmale überleben kaputtes Modell-JSON (AK 7).
- [ ] Interview ohne Antworten → Ergebnis ohne Merkmale, kein Fehler (AK 8).

### Docs

- [ ] `docs/decisions/034-interview-fuellt-merkmale.md`: Kontext / Optionen / Entscheidung /
      Konsequenzen. Kernpunkt: Merkmale werden **gefragt**, nicht aus Prosa geraten; der
      Modell-Pfad ist optional, auf leere Felder beschränkt und als `inferred` markiert; ADR-009
      wird präzisiert, nicht aufgehoben.

## Report-Back
