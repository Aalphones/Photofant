# Phase 7 — Wizards: Interview nach Design + Web-Suche mit Fakten-Bestätigung

**Komplexität:** standard (der Interview-Dialog existiert und wird umgezogen; der Web-Wizard
folgt derselben Hülle und hat einen klar definierten Kontrakt aus Phase 3/4).
**Voraussetzung:** Phase 4 (beide Routen), Phase 5 (die Knöpfe, die hier landen).

Beide Wizards teilen sich Rahmen, Kopf und Fußleiste. Erst die gemeinsame Hülle bauen, dann die
zwei Inhalte — nicht zwei Dialoge nebeneinander, die sich zufällig ähneln.

## Design-Referenz
- `design/README.md` Abschnitte „3. Interview-Wizard" und „4. Web-Suche-Wizard".
- `design/styles.css` Zeile 1462-1485 (`.kw-wiz` … `.kw-fact-src`).
- `design/js/data.js` Zeile 455-461 — die fünf Interview-Fragen im Wortlaut.

## Kontext (lesen vor dem Start)
- `frontend/src/app/features/wissen/interview-dialog/interview-dialog.{ts,html,scss}` — **166
  Zeilen, komplett lesen.** Der Ablauf (Fragen, Antworten sammeln, Synthese anfordern, Ergebnis
  übernehmen) bleibt; Aussehen und Schrittfolge wandern auf das Design.
- `frontend/src/app/services/knowledge.service.ts` — `requestInterviewSynthesis`,
  `requestDiscovery`/`applyDiscovery` (Phase 4), `createEntity`.
- `frontend/src/app/services/jobs.service.ts` — `streamJobs()`. Muster für „auf Job-Ende warten":
  `lore-panel.ts` Zeile 150-234.
- `frontend/src/app/models/knowledge.model.ts` — `KnowledgeDiscoveryResult`,
  `KnowledgeDiscoveryFact`, `DiscoveryApplyRequest`, `KnowledgeInterviewResult`.
- `frontend/src/app/store/persons/persons.selectors.ts` — Personen für die Auswahl-Chips.

## Aufgabe 1 — Gemeinsame Wizard-Hülle
Neu: `features/wissen/wizard-shell/wizard-shell.{ts,html,scss}`, Selektor `pf-wizard-shell`.

Eingänge: `title = input.required<string>()`, `canGoBack = input(false)`,
`primaryLabel = input<string | null>(null)`, `primaryDisabled = input(false)`.
Ausgänge: `close`, `back`, `primary`.

Rahmen exakt nach `design/styles.css` Zeile 1462: `width: min(500px, 92vw); max-height: 86vh;
display: flex; flex-direction: column;` auf `--surface`, 1px `--line-2`, `border-radius: 14px`,
`--shadow-pop`, `overflow: hidden`. Körper `padding: 18px 20px; overflow-y: auto; flex: 1;
min-height: 120px`. Fußleiste `display: flex; justify-content: space-between; padding: 14px 20px;
border-top: 1px solid var(--line); flex: none;` — links „Zurück" (wenn `canGoBack`), rechts der
Hauptknopf.

Escape und Scrim-Klick schließen. Beim Öffnen den Fokus auf das erste Eingabefeld setzen.

## Aufgabe 2 — Interview-Wizard
Bestehenden `interview-dialog` in die Hülle umziehen. Schrittfolge:

**Schritt 0 — Person wählen.** Chips der bekannten Personen (`.kw-iv-pick-row`, umbrechend) plus
darunter — abgetrennt durch eine Zeile „ODER" (11px, Großbuchstaben, `letter-spacing: .08em`,
`--text-3`) — ein Freitext-Feld für einen Namen ohne Foto-Person. Wird der Wizard aus einem
Personen-Kontext geöffnet (Karte, Detail, Aufgabe), entfällt der Schritt: stattdessen eine
Bestätigungszeile „Interview mit {Name}" (`.kw-iv-preset`, 12px Abstand).

**Schritte 1..N — je eine Frage.** Fortschrittszeile „Frage {X} von {N}" (11px, `--mono`,
`--text-3`), Frage als Label (13px/600), darunter ein Textfeld (`min-height: 90px`,
`--bg-2`, 1px `--line-2`, `border-radius: 9px`, Fokus: `--accent-line` + 3px `--accent-weak`).
**Leer lassen ist erlaubt** — der Hauptknopf heißt dann „Überspringen" statt „Weiter". Ohne diese
Umbenennung wirkt ein leeres Pflichtfeld wie ein Fehler.

Die fünf Fragen wörtlich aus `design/js/data.js` Zeile 455-461 übernehmen, als Konstante
`INTERVIEW_QUESTIONS` in der Komponente (nicht im Backend — sie sind reine Oberfläche).

**Schritt N+1 — Warten.** Zentrierter Spinner mit „Antworten werden zu einem Kurzprofil
zusammengefasst…". Kein `setTimeout` wie im Prototyp: auf den echten Job warten
(`requestInterviewSynthesis` → `streamJobs()` bis `done`/`error`).

**Schritt N+2 — Ergebnis.** Überschrift „Kurzprofil" (12.5px/600, `--text-2`), darunter der
synthetisierte Text, darunter die Herkunfts-Zeile (`.kw-explain`, 11.5px, `--text-3`, mit
Info-Icon): „Aus {N} Antworten · Modell {model_id} · Prompt {prompt_version} · Konfidenz {N} %".
Fußleiste: links „Antworten anpassen" (zurück auf Schritt 1), rechts „Übernehmen".

**Ohne gewählte Person** landet das Ergebnis als eigenständige, unverknüpfte Notiz — es wird
**nie** verworfen. Das ist die Regel aus dem Design und gleichzeitig der Grund, warum es die
Sektion „Nicht verknüpfte Notizen" gibt.

## Aufgabe 3 — Web-Suche-Wizard
Neu: `features/wissen/web-search-dialog/web-search-dialog.{ts,html,scss}`, Selektor
`pf-web-search-dialog`, in derselben Hülle.

**Schritt 0 — Person + Hinweise.** Dieselben Auswahl-Chips wie im Interview, dazu ein optionales
einzeiliges Feld (36px hoch) mit Platzhalter „z. B. Beruf, Stadt oder ein Link — hilft beim
Finden". Der Text geht als Teil der Suchanfrage mit. Hauptknopf: „Suchen".

**Schritt 1 — Suche läuft.** Zentrierter Spinner: „Gemma durchsucht öffentliche Quellen für
{Name}…". Warten auf den Job aus Phase 3 über `streamJobs()`, nicht auf einen Timer.

**Schritt 2 — Ergebnisliste.** Je Fakt eine Zeile (`.kw-fact-row`): `padding: 10px 9px`,
`--bg-2`, 1px `--line`, `border-radius: 9px`, 8px Abstand nach unten.
- Checkbox 16px, `accent-color: var(--accent)`, **standardmäßig aktiv**.
- Feldname 10.5px, Großbuchstaben, `letter-spacing: .06em`, `--text-3`.
- Wert 12.5px, `--text`.
- Rechts die Quell-Domain (11px, `--mono`, `--text-3`) und eine Konfidenz-Pille — bestehende
  `score-pill`-Klasse des Projekts wiederverwenden (grep `score-pill`), Schwelle: ab 0.75 „high",
  darunter „mid".
- Fußknopf: „{N} Fakten übernehmen", `[disabled]` wenn nichts angehakt ist.

Leere Ergebnisliste → statt der Liste ein Satz: „Nichts Belastbares gefunden. Ein Hinweis wie
Beruf oder Stadt hilft oft." plus Knopf „Nochmal mit Hinweis".

**Schritt 3 — Ergebnis der Übernahme.** `applyDiscovery` liefert `written_fields`,
`created_entities` und `errors`. Alle drei anzeigen, jede Gruppe als eigene Zeile:
- „{N} Merkmale übernommen."
- „Neu angelegt: {Titel}, {Titel}" (falls Entitäten vorgeschlagen und angelegt wurden)
- Jede `errors`-Zeile im Wortlaut des Backends — insbesondere die Meldung, dass ein von dir
  gesetzter Wert unangetastet blieb. **Das ist kein Fehler, sondern die wichtigste Rückmeldung
  des ganzen Ablaufs** und darf nicht in Rot oder als Warnung erscheinen; normale Textfarbe,
  Info-Icon.

## Aufgabe 4 — Verdrahtung
`wissen.ts`: beide Wizards öffnen aus der Kopfzeile (Phase 5), aus dem Detail-Kopf (Phase 6),
aus einer Aufgaben-Chip (Phase 5) und — nach Phase 8 — aus Personen-Karte und Lightbox. Ein
gemeinsames Signal `wizardTarget = signal<{ personId: number | null; name: string | null } | null>(null)`
trägt die Vorbelegung; die Wizards lesen nur daraus, sie holen sich nichts selbst.

Nach erfolgreichem Abschluss beider Wizards: Entities und Aufgaben neu laden (bestehende
Store-Aktionen) und den Toast aus Phase 5 auslösen.

## Idiotensicherheit
- Vor dem ersten Suchknopf steht ein Satz, was gleich passiert: „Sucht im Netz nach öffentlich
  verfügbaren Angaben. Du entscheidest danach, was übernommen wird." Ein eigener Warn-Dialog
  ist **nicht** nötig — es wird nichts ohne Zutun geschrieben (das war im ursprünglichen
  Entwurf anders).
- Die Konfidenz-Pille bekommt ein `title`: „Wie sicher sich das Modell ist — keine Garantie."
- „Überspringen" statt „Weiter" bei leerem Antwortfeld (Aufgabe 2).

## AK dieser Phase
- [x] Beide Wizards nutzen dieselbe Hülle: 500px breit, Fußleiste mit Trennlinie,
      Escape/Scrim/X schließen.
- [x] Interview: Personen-Wahl per Chip **oder** Freitext; aus einem Personen-Kontext geöffnet
      entfällt der Schritt und zeigt stattdessen die Bestätigungszeile.
- [x] Interview: leeres Antwortfeld → Knopf heißt „Überspringen"; die Fortschrittszeile zählt
      korrekt „Frage X von N".
- [x] Interview ohne gewählte Person legt eine unverknüpfte Notiz an, die danach in der
      Übersicht auftaucht.
- [x] Web-Suche: Ergebnisliste mit vorab aktiven Checkboxen, Quell-Domain und Konfidenz-Pille;
      Fußknopf zählt die angehakten Fakten mit.
- [x] Web-Suche: nach der Übernahme werden übernommene Merkmale, neu angelegte Entitäten **und**
      übersprungene Werte angezeigt — letztere sachlich, nicht als Fehler.
- [x] Kein `setTimeout` als Ladesimulation im ausgelieferten Code; beide Ladezustände hängen am
      echten Job-Stream.
- [x] `npx tsc --noEmit` grün, Produktions-Build läuft durch.

## Doc-Updates
- [x] `docs/code-map.md` — `features/wissen/wizard-shell/` und `web-search-dialog/` ergänzt.

## Report-Back

**Umgesetzt wie geplant:** gemeinsame `wizard-shell` (Aufgabe 1), Interview komplett auf
Personen-Chip/Freitext + fünf feste Fragen umgeschnitten (Aufgabe 2), neuer
`web-search-dialog` self-contained wie `lore-panel.ts` (Aufgabe 3), Verdrahtung über ein
gemeinsames `wizardTarget`-Signal (Aufgabe 4). `npx tsc --noEmit` grün, Produktions-Build
läuft durch (gleiche vorbestehende Bundle-Budget-Warnung wie Phase 5/6, keine Regression).
Backend: `ruff`/`mypy` grün, `test_knowledge_discovery_job.py` (19 Tests) weiter grün.

**Abweichungen vom Plan-Wortlaut (mit Begründung):**
1. **`WizardTarget` um `entityId` erweitert** (Plan: nur `{personId, name}`). Web-Suche kann
   auf jeder nicht-privaten Entity laufen (Detail-Kopf-Button `canRequestWebSearch`), auch auf
   einer unverknüpften Notiz ohne Personen-Bezug (z.B. Movies-Domäne) — mit nur `personId`
   wäre dieser Fall nicht adressierbar gewesen. Abwärtskompatibel (zusätzliches Feld).
2. **`missing_field`/`low_completeness`-Aufgaben umgeleitet:** Diese Aufgaben-Chips öffneten
   bisher den Entity-Wizard — der kennt aber gar keine Merkmale (`attributes`), kann das
   Problem also nie beheben (vorbestehende Lücke seit Phase 4/5, hier beim Verdrahten
   aufgefallen und mitgefixt). Sie öffnen jetzt die Web-Suche, vorbelegt mit der betroffenen
   Entity (`personIdByEntityId`-Umkehr-Map löst die Person auf, falls verknüpft).
3. **`DiscoveryRequest` um optionales `hint` erweitert** (Backend `api/knowledge_ai.py` +
   `jobs/knowledge_discovery_job.py`, Frontend `knowledge.model.ts`). Der Plan verlangt ein
   Hinweisfeld im Web-Suche-Wizard, das „als Teil der Suchanfrage" mitgeht — der Phase-3/4-
   Kontrakt kannte dafür kein Feld. Additiv, kein bestehender Aufrufer betroffen (Default
   `None`), fließt nur in die `search_web()`-Anfrage ein, kein eigener Prompt-Slot. Grund für
   den Cross-Phase-Eingriff: ohne ihn wäre das Hinweisfeld eine Attrappe gewesen.
4. **`score-pill`-Klasse lokal nachgebaut statt wiederverwendet** (Plan: „bestehende
   `score-pill`-Klasse … wiederverwenden"). Die einzige bestehende Instanz (`review-faces.scss`
   `.rf__score-pill`) ist Angular-komponenten-gescoped, kein globaler Export — in
   `web-search-dialog.scss` nach derselben Konvention (Mono-Schrift, `high`/`mid`-Farbe) neu
   angelegt statt eines nicht möglichen Fremd-Imports.
5. **Pet-Interview entfällt.** Die alte Interview-Umsetzung unterschied Person/Pet mit eigenen
   Fragen; das Design hat nur einen festen, personenbezogenen Fragensatz (Frage 4: „Wie würdest
   du eure Beziehung zueinander beschreiben?" passt nicht auf ein Haustier) und keine
   Typ-Auswahl mehr. Interview legt jetzt immer den `Person`-Typ der privaten Domäne an —
   Haustiere lassen sich weiterhin über „Neue Entity" (Entity-Wizard, Domäne „Private", Typ
   „Pet") anlegen, nur nicht mehr über den geführten Dialog.
6. **`wizard-shell` um `backLabel`/`hideFooter` erweitert** (Plan nennt nur `title`/`canGoBack`/
   `primaryLabel`/`primaryDisabled`). Nötig, damit der Summary-Schritt „Antworten anpassen"
   statt „Zurück" zeigen kann und die Synthese-/Such-Ladephasen ganz ohne Fußleiste auskommen
   (Design zeigt dort keine Knöpfe).

**Bekannte Grenze (nicht behoben, dokumentiert):** Navigiert man im Wissen-Detail-Modal über
einen Beziehungs-Chip auf eine andere Person und öffnet danach „Interview"/„Web-Suche", zielt
der Wizard noch auf die ursprünglich geöffnete Person, nicht die intern nachnavigierte — der
Output von `KnowledgeDetailDialog` ist unverändert `void`, träfe eine Erweiterung nur für
diesen Randfall.

**Live-Smoke steht aus** (privates Profil, kein Server/Browser in dieser Session):
Wizard-Öffnen aus allen vier Einstiegen, Interview-Flow bis Anlegen, Web-Suche-Flow bis
Übernahme inkl. `hint`-Feld — siehe Plan-Ende-Checkliste in der README.
