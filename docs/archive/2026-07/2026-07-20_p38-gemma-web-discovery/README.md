# P38 — Wissen: Web-Recherche + neue Oberfläche

> Zwei Stränge in einem Plan. **Backend (Phase 1-4):** Gemma bekommt bei explizitem Klick echte
> Web-Suchergebnisse als Kontext und schlägt daraus Fakten vor; dazu die bisher fehlende
> Merkmals-Struktur (Felder mit eigenem Owner) samt Vollständigkeits-Wert. **Frontend (Phase
> 5-8):** die Wissens-Oberfläche aus dem Design-Handoff (`design/`) — Übersicht, Detail,
> beide Wizards, Personen-Karte, Lightbox-Tab.
> Baut auf P27 (Gemma-Integration, noch nicht archiviert — Smoke steht aus) und erweitert
> dessen Capability-Layer (ADR-027/028) um eine vierte Fähigkeit.
> *(private, lean — Vollplan: neue Architektur, Schema-Änderung, zwei neue ADRs.)*

## Phasen
| # | Phase | Komplexität | Status |
|---|---|---|---|
| 1 | Fundament — Web-Suche, Capability, Einstellung, ADR-031 | heikel | ✅ complete |
| 2 | Merkmale + Vollständigkeit (Schema, Felddefinitionen, ADR-032) | heikel | ✅ complete |
| 3 | KnowledgeDiscoveryJob — Suche → Gemma → Fakten-**Vorschläge** | heikel | 🟡 Code+Tests fertig, Live-Check blockiert (kein Modell gebunden) |
| 4 | Routen + Guards + neue Aufgaben-Arten | standard | 🟡 Code fertig, Live-Smoke steht aus |
| 5 | Wissen-Übersicht nach Design | standard | ✅ complete |
| 6 | Wissen-Detail (Modal) nach Design | standard | ✅ complete |
| 7 | Wizards — Interview + Web-Suche mit Fakten-Bestätigung | standard | ✅ complete |
| 8 | Personen-Karte + Lightbox-Wissen-Tab | standard | ✅ complete |

## Ziel
Wissen über Personen wird sichtbar, messbar und befüllbar. Sichtbar: eine Übersicht mit
Personen-Karten statt der heutigen flachen Entity-Liste, jede mit Vollständigkeits-Ring.
Messbar: Merkmale sind ab jetzt echte Felder mit eigenem Owner (Manuell / Web / KI-Schätzung /
leer), nicht mehr nur Fließtext. Befüllbar: zwei Wege — privates Interview (gibt es schon,
kriegt die Design-Oberfläche) und Web-Recherche (neu: Gemma sucht öffentlich verfügbare Fakten
und legt sie dir zur Bestätigung vor).

## Vorgeschichte — was der User entschieden hat
1. **Web-Zugriff:** Opt-in pro Aktion. Kein Hintergrund-/Auto-Trigger — Websuche läuft
   ausschließlich, wenn der User an einer konkreten Entity auf „Recherchieren" klickt.
2. **Schreibverhalten (2026-07-21 revidiert):** Web-Fakten werden **bestätigt, nicht automatisch
   geschrieben** — Ergebnisliste mit Checkboxen (Standard: alle aktiv), Footer-Knopf
   „N Fakten übernehmen". Der ursprüngliche P38-Entwurf sah Auto-Write ohne Rückfrage vor; das
   Design-Handoff zeigt den Bestätigungs-Weg, und der User hat ihm den Vorrang gegeben. Folge:
   die geplante Ausnahme von der P27-Kernregel „Gemma ändert nie direkt Daten" **entfällt** —
   ADR-031 regelt nur noch den Netzwerkzugriff, nicht mehr den Schreibweg. Kein Erklär-Dialog
   beim Erstklick mehr nötig (es gibt nichts mehr zu warnen).
3. **Merkmale (2026-07-21 entschieden):** die Feld-Struktur mit eigenem Owner pro Merkmal wird
   **gebaut** (Phase 2), nicht gefaked und nicht weggelassen — sie trägt Ring, Prozentwert,
   Owner-Farben und zwei der fünf Aufgaben-Arten aus dem Design.
4. **Private Entitäten:** kein neuer Ergänzen-Weg nötig — geprüft (`lore-panel.ts`), das
   bestehende „Ergänzen (KI)" aus P27 Phase 3 ist bereits webfrei und läuft schon heute
   uneingeschränkt auch auf privaten Entitäten (kein ADR-009-Konflikt, da kein Web-Zugriff).

## Design-Handoff — was gilt
Das Bundle liegt **im Plan** unter `design/` (kopiert aus dem Handoff, damit die Phasen ohne
externe Pfade lesbar bleiben). Es ist ein React/Babel-Prototyp mit Mock-Daten — **Referenz für
Look, Struktur und Interaktion, kein Produktionscode zum Kopieren**. Nachgebaut wird im
bestehenden Angular-Frontend mit Signals, Standalone-Components und dem NgRx-`knowledge`-Slice.

Verbindlich (Design-Deckung vorhanden → Pixel-Treue): Übersicht, Detail-Modal, beide Wizards,
Personen-Karten-Chip, Lightbox-Tab. Maße und Farbwerte stehen in `design/styles.css`,
Abschnitt „WISSEN" (Zeile 1383-1499) — die Phasen zitieren die relevanten Werte, damit niemand
in der CSS-Datei suchen muss.

**Aus dem Design bewusst nicht übernommen:** die Box „Album-Vorschlag" im Detail-Modal. Dahinter
steckt eine KI-Funktion, die es nirgends gibt (aus Fotos + Wissen ein Album vorschlagen) — eine
eigene Capability, eigener Job, eigener Plan. Wird ersatzlos weggelassen, nicht als toter Rahmen
gebaut. Alles andere aus dem Handoff ist eingeplant.

## Wichtige Funde vor dem Planen

**Der Kern der Web-Recherche ist billiger als gedacht.** `inference/tools.py` (`ToolRegistry`)
ist unbenutztes Scaffolding — die bestehenden Jobs rufen `generate()` und `KnowledgeService`
direkt auf, es gibt keinen Agenten-Loop mit Funktionsaufrufen. Eine echte agentische Suche wäre
ein neuer, riskanter Baustein ohne Bedarf. Stattdessen derselbe deterministische Single-Shot-Stil
wie die bestehenden Jobs: Suche läuft **vor** dem Gemma-Call (Python entscheidet die Suchanfrage),
Ergebnisse gehen als Kontext in den Prompt, Gemma liefert strukturierten Text, der geparst wird.
`ToolRegistry` bleibt unangetastet.

**`Owner.WEB` und `entity.sources` existieren bereits** (`knowledge/schema.py`), inklusive
korrekter Überschreib-Priorität (`user > manual > web > inferred`) und im Frontend-Typ `OWNERS`
mitgeführt. Die Lore-Panel-„Quellen"-Sektion rendert jede Liste automatisch. Fundament da,
Risiko runter.

**Merkmale gibt es dagegen nicht — verifiziert, nicht vermutet.** `Entity` (`knowledge/schema.py`
Zeile 69-90) hat **einen** Owner für die ganze Einheit und einen Freitext-`body`. Kein
Feld-Container, keine Felddefinitionen, kein Vollständigkeits-Wert (`grep -rn "completeness"
backend/photofant` trifft nur `models/validation.py`, ein anderer Kontext). `owner_can_overwrite`
existiert, wird aber nur auf Entity-Ebene angewendet (`service.py` Zeile 352). Das gesamte
Merkmals-Kapitel des Designs — Ring, „N %", Owner-Pillen, die Aufgaben „Feld fehlt" und „kaum
ausgefüllt" — hängt an dieser einen fehlenden Struktur. Deshalb eine eigene, frühe Phase.

**Drei der fünf Aufgaben-Arten aus dem Design fehlen.** Vorhanden (`knowledge/tasks.py`
Zeile 20-25): `new_person`, `missing_entity`, `confirm_relationship`, `review_recommendation`,
`incomplete_entity`. Neu nötig: `missing_field`, `low_completeness`, `auto_link`.

**Vier Design-Bausteine stehen schon:** der Wissen-Tab in der Lightbox (`lightbox.html` Zeile
353-391, mit `pf-lore-panel` + Empfehlungen), der Verknüpfungs-Chip auf der Personen-Karte
(`person-card.html` Zeile 80-89, ohne Prozentwert), `interview-dialog/` und
`link-entity-dialog/`. Phase 7 und 8 erweitern, statt neu zu bauen.

## Kontrakt (Backend ↔ Frontend)

### Merkmale + Vollständigkeit (Phase 2)
Domänen-YAML, pro Entity-Typ optional:
```yaml
entity_types:
  - name: Person
    folder: personen
    fields:
      - key: geburtstag
        label: Geburtstag
      - key: beruf
        label: Beruf
```

Backend-Schema (`knowledge/schema.py`):
```python
@dataclass
class Attribute:
    value: str
    owner: Owner = Owner.INFERRED
    confidence: float = 1.0

# Entity bekommt zusätzlich:
attributes: dict[str, Attribute] = field(default_factory=dict)
```

Frontend (`models/knowledge.model.ts`):
```ts
export interface AttributeDto { value: string; owner: Owner; confidence: number; }
export interface EntityFieldDefDto { key: string; label: string; }

// EntityDto bekommt zusätzlich:
attributes: Record<string, AttributeDto>;
completeness: number;   // 0..1, berechnet, nie gespeichert

// EntityType bekommt zusätzlich:
fields: EntityFieldDefDto[];

// EntityRefDto bekommt zusätzlich (für Personen-Karte + Übersicht ohne Extra-Request):
completeness: number;
```

**Vollständigkeit** = Anzahl der Merkmale mit nicht-leerem Wert geteilt durch Anzahl der für den
Typ definierten Merkmale. Kein definiertes Merkmal → `0.0`. Wird bei jedem Ausliefern berechnet,
**nie** persistiert (sonst driftet sie gegen die Markdown-Wahrheit, ADR-025).

Die **Merkmale selbst** liegen zusätzlich in der Cache-Spalte `knowledge_entities.attributes`
(JSON, gleiche Form wie im Frontmatter, migration 0040 — Phase 2). Reine Spiegelung wie die
Aliase, damit Listen-Ansichten den Prozentwert liefern können, ohne pro Zeile eine Markdown-Datei
zu öffnen. Der Prozentwert selbst bleibt draußen.

### Web-Recherche (Phase 3/4)
- **Neue Capability:** `Capability.KNOWLEDGE_DISCOVERY = "knowledge_discovery"`.
- **Neuer Job-Kind:** `JobKind.KNOWLEDGE_DISCOVERY = "knowledge_discovery"` (Backend `jobs/queue.py`,
  Frontend `JOB_KINDS` in `models/job.model.ts`).
- **Recherche starten:** `POST /api/knowledge/ai/discovery` · Body `{ entity_id: string; hint?: string }` ·
  Response `{ job_id: string }`. 409 wenn `ai.autonomy.discovery != "auto"`, 422 wenn die
  Ziel-Domäne privat ist, 404 wenn die Entity fehlt. `hint` additiv seit Phase 7 (Web-Suche-
  Wizard, „Beruf, Stadt oder ein Link") — geht nur in die Suchanfrage ein, kein Prompt-Slot.
- **Job-Ergebnis** (`JobDto.result`) — **reine Vorschläge, nichts ist geschrieben**:
  ```ts
  interface KnowledgeDiscoveryFact {
    field: string;        // Merkmals-Key aus der Domäne, oder 'body'
    label: string;        // Anzeigename ('Beruf', 'Beschreibung')
    value: string;
    source: string;       // Host der Quelle, z.B. 'linkedin.com'
    source_url: string;
    confidence: number;   // 0..1
  }
  interface KnowledgeDiscoveryEntitySuggestion {
    title: string; type: string; relationship_type: string; body: string;
  }
  interface KnowledgeDiscoveryResult {
    facts: KnowledgeDiscoveryFact[];
    entity_suggestions: KnowledgeDiscoveryEntitySuggestion[];
    sources: string[];
    errors: string[];
    explainability: { model_id: string; capability: string; prompt_version: string;
                      duration_ms: number; confidence: number | null; reason: string };
  }
  ```
- **Bestätigte Fakten übernehmen:** `POST /api/knowledge/ai/discovery/apply` ·
  Body `{ entity_id: string; facts: KnowledgeDiscoveryFact[]; entity_suggestions: KnowledgeDiscoveryEntitySuggestion[] }` ·
  Response `{ written_fields: string[]; created_entities: { id: string; title: string; type: string }[]; errors: string[] }`.
  Synchron (kein Job — es läuft kein Modell mehr, nur Schreiben). Schreibt mit `owner=web`,
  respektiert `owner_can_overwrite` pro Merkmal, schreibt Changelog-Einträge und ergänzt
  `entity.sources`.
- **Autonomie-DTO erweitert:** `AutonomyDto` bekommt `discovery: string` (`"off" | "auto"`,
  kein `"ask"` — die Bestätigung sitzt jetzt im Wizard, nicht im Autonomie-Schalter).

### Aufgaben (Phase 4)
`TaskKind` bekommt `MISSING_FIELD = "missing_field"`, `LOW_COMPLETENESS = "low_completeness"`,
`AUTO_LINK = "auto_link"`; `TASK_KINDS` im Frontend spiegelt das. Context-Felder:
```ts
missing_field    → { entity_id, title, fields: string[] }
low_completeness → { entity_id, title, completeness: number }
auto_link        → { entity_id, title, person_id: number, person_name: string, score: number }
```

## Finale AK (Gesamt)
- [ ] Auf einer **öffentlichen** Entity löst „Recherchieren" eine echte Websuche aus (sichtbar im
      Job-Dock); das Ergebnis ist eine Fakten-Liste zum Abhaken, nichts wird ungefragt geschrieben.
- [ ] Übernommene Fakten tragen `owner: web`; ein `user`/`manual`-Merkmal wird nie überschrieben,
      auch nicht wenn der Haken gesetzt ist (Backend gewinnt, Frontend zeigt es an).
- [ ] Jede Übernahme erzeugt Changelog-Einträge (sichtbar über „Warum geändert?") und trägt die
      verwendeten Quell-URLs in `entity.sources`.
- [ ] Auf einer **privaten** Entity wird „Recherchieren" gar nicht erst angeboten (Frontend) und
      die Route lehnt mit 422 ab (Backend-Guard, Verteidigung in der Tiefe).
- [ ] `ai.autonomy.discovery` steuert die Funktion global ab-/anschaltbar (Default `off`).
- [ ] Merkmale sind pro Entity sichtbar mit Wert und Owner-Pille; fehlende Merkmale erscheinen
      als eigene Zeile mit gestrichelter „fehlt"-Pille.
- [ ] Der Vollständigkeits-Ring zeigt denselben Prozentwert wie die Merkmals-Liste hergibt
      (nachrechenbar: gefüllte durch definierte Merkmale).
- [ ] Die Wissen-Übersicht zeigt Personen-Karten mit Ring, die Aufgaben-Reihe und — falls
      vorhanden — die Sektion „Nicht verknüpfte Notizen".
- [ ] Eine Notiz ohne Person und eine Person mit ähnlichem Namen erzeugen eine
      Verknüpfungs-Aufgabe; ein Klick darauf öffnet die Personen-Auswahl mit vorgewähltem Treffer.
- [ ] „Verknüpfung lösen" trennt die Zuordnung, ohne die Notiz zu löschen — sie taucht danach
      unter „Nicht verknüpfte Notizen" auf.
- [ ] Personen-Karte zeigt bei vorhandenem Wissen einen Chip mit Prozentwert, sonst den
      gestrichelten Nudge „Wissen anlegen?" — beides öffnet die Wissen-Detailansicht.
- [ ] Smoke bestätigt zusätzlich: das bestehende „Ergänzen (KI)" funktioniert bereits heute auf
      privaten Entitäten (keine neue Arbeit, nur Verifikation).

## Risiken
- 🟡 **Schema-Änderung an der Markdown-Wahrheit** (Phase 2) — `attributes` kommt neu ins
  Frontmatter. Bestehende Vault-Dateien haben den Block nicht. Mitigation: `attributes` ist
  optional mit Default `{}`, der Vault-Reader toleriert Abwesenheit, es gibt **keine** Migration
  bestehender Dateien (sie bekommen den Block, sobald zum ersten Mal ein Merkmal geschrieben
  wird). Der Round-Trip (lesen → schreiben → lesen) ist der Prüfpunkt, nicht die Migration.
- 🟡 **Kleines lokales Modell (4B/12B) parst Suchergebnisse unzuverlässig** — Freitext-Parsing
  statt striktem JSON (robuster bei kleinen Modellen), defensiver Parser degradiert auf „keine
  Fakten gefunden" statt zu crashen. Konkreter Check: Phase 3, Abschnitt „Parser-Test". Durch
  den Bestätigungs-Weg ist der Schaden bei Fehlparsing jetzt kosmetisch statt datenverändernd.
- 🟡 **Web-Suchpaket-API kann sich ändern** (`ddgs`, kein offizieller SLA) — Phase 1 verifiziert
  die aktuelle API-Form gegen die installierte Version, bevor der Rest darauf aufbaut.
- 🟡 **Namens-Match für die Verknüpfungs-Aufgabe** (Phase 4) — reine Ähnlichkeit über
  `difflib.SequenceMatcher`, kein phonetisches Matching. Erzeugt bei Namensvettern falsche
  Vorschläge. Bewusste Grenze: der Vorschlag muss ohnehin bestätigt werden.
- 🟡 **Duplikat-Entitäten** — Namensgleichheit ist der einzige Dedup-Check beim Anlegen
  vorgeschlagener Entitäten (kein Fuzzy-Matching in v1). Dokumentiert statt versteckt.

## Bewusst draußen (Feature-Radar, max. 1 Punkt — hier verbraucht)
**Volltext-Scraping der gefundenen Seiten** (statt nur Titel/Snippet aus der Suche) würde die
Qualität der Vorschläge deutlich heben, braucht aber einen HTML-Boilerplate-Extractor und mehr
Netzwerk-Zeit pro Klick. Backlog-Kandidat, kein Blocker für v1 — sag Bescheid, falls das jetzt
schon mit rein soll, sonst bleibt's bei Snippet-only.

## Konfidenz-Ausweis
1. **Am unsichersten: hält ein 4B/12B-Modell das Fakten-Format ein?** Der Prompt verlangt Zeilen
   der Form `- Feld: … | Wert: … | Quelle: … | Konfidenz: …`. Die Alt-Jobs prüfen nur „ist die
   Antwort leer", nicht Format-Treue. **Check:** Phase 3, nach der ersten echten Generierung
   5-10 Läufe gegen verschiedene reale öffentliche Personen, Trefferquote des Parsers
   protokollieren, bevor Phase 4 draufbaut. Bei unter der Hälfte: Prompt nachschärfen
   (Beispiel-Output aufnehmen), **nicht** den Parser komplizierter machen.
2. **Frontmatter-Round-Trip der Merkmale** (Phase 2) — Entwarnung nach Blick in
   `knowledge/parser.py`: `media_links` ist bereits ein verschachtelter Block, die Maschinerie
   (`python-frontmatter` + PyYAML, `sort_keys=False`) trägt das nachweislich. Rest-Unsicherheit
   nur bei Sonderzeichen in Werten (Doppelpunkt, Umlaute, lange Texte). **Check:** Phase 2
   Aufgabe 3 — Entity mit drei solchen Merkmalen speichern, Datei ansehen, neu laden, auf
   Gleichheit prüfen. Steht als erster AK-Punkt der Phase.
3. **`ddgs`-Paketname und Rückgabe-Keys** — **Check:** `uv add ddgs` + ein Interaktions-Test in
   Phase 1, bevor der Rest darauf aufbaut.

## Smoke-Checkliste (du prüfst am Plan-Ende)
Wackelstellen zuerst (Konfidenz-Ausweis oben):
1. **Merkmale überleben das Speichern:** Bei einer Person drei Merkmale eintragen, Anwendung neu
   laden — Werte, Owner-Farben und Prozentwert stehen unverändert da. Dann dieselbe
   Markdown-Datei im Vault öffnen und schauen, ob sie noch les- und editierbar aussieht.
2. **Parser-Robustheit:** 3-5 „Recherchieren"-Läufe auf verschiedenen realen, bekannten
   öffentlichen Personen → die Fakten-Liste zeigt jedes Mal etwas Sinnvolles (nicht leer, nicht
   kaputt), auch wenn Gemma mal vom Format abweicht.
3. **User-Werte bleiben unantastbar:** Ein Merkmal, das du zuvor manuell gesetzt hast, wird durch
   eine bestätigte Web-Übernahme **nicht** überschrieben — es taucht in `errors` als übersprungen
   auf, statt still zu verschwinden.
4. **Kein Auto-Trigger:** `ai.autonomy.discovery` bleibt nach Neuinstallation auf `off` — der
   Knopf ist nirgends sichtbar, ohne dass du ihn manuell aktivierst.
5. **Private Entität geschützt:** Auf einer privaten Person taucht der Knopf nirgends auf, ein
   direkter API-Aufruf liefert 422.
6. **Verknüpfen und Lösen:** Eine Notiz per Aufgabe mit einer Person verknüpfen, dann im Detail
   „Verknüpfung lösen" — die Notiz landet unter „Nicht verknüpfte Notizen", kein Datenverlust.
7. **Changelog + Quellen sichtbar:** nach einer Übernahme zeigt „Warum geändert?" die neuen
   Einträge, die „Quellen"-Sektion listet die verwendeten URLs.
8. **Bestehendes „Ergänzen (KI)" auf privaten Entitäten:** einmal testen, dass das (bereits heute
   existierende, webfreie) „Ergänzen (KI)" auf einer privaten Person weiterhin funktioniert —
   reine Verifikation, keine neue Funktion.

## Bottom-Sektionen

### Summary
Web-Recherche (Gemma + echte Websuche, nur bei explizitem Klick, nur auf öffentlichen
Entitäten) und die komplett neue Wissens-Oberfläche aus dem Design-Handoff: Übersicht mit
Personen-Karten + Vollständigkeits-Ring, Detail-Modal, zwei Wizards (Interview/Web-Suche),
Personen-Karten-Chip und Lightbox-Wissen-Tab. Merkmale sind jetzt echte Felder mit eigenem
Owner statt Freitext, Vollständigkeit eine reine, nie gespeicherte Ableitung. Zwei AK-Punkte
(Phase 3 Parser-Trefferquote, Phase 4 API-Live-Smoke) warten weiter auf einen gebundenen
Gemma-Lauf bzw. den User-Smoke — siehe STATE.md „Offene Smoke-Tests".

### Files touched
**Backend:** `knowledge/` (schema/domains/parser/validator/service/repository/task_rules,
neu: `slug.py`), `jobs/knowledge_discovery_job.py`, `api/knowledge.py` + `api/knowledge_ai.py`,
`api/persons.py`/`api/assets.py` (EntityRefDto.completeness), Migration 0040, ADR-031/032.
**Frontend:** `features/wissen/` (komplett neu: wissen.ts/html, knowledge-detail-dialog/,
interview-dialog/, web-search-dialog/, wizard-shell/, work-queue/, person-knowledge-card/,
entity-wizard-dialog/ erweitert), `features/personen/` (personen.ts/html + person-card/ —
Wissens-Chip/Nudge + lokales Detail-Modal), `features/galerie/lightbox/` (lightbox.ts/html +
lore-panel/ — Ring/Profil-Link/Weitere-Bilder/Recherchieren, alte Inline-Wizard-Lösung entfernt),
`ui/completeness-ring/` (neu), `ui/link-entity-dialog/` (verschoben + zweiter Modus),
`models/knowledge.model.ts`.

### Commits
Siehe `git log` auf diesem Branch — ein Commit pro Phase (Konvention `mode-committing`), zuletzt
Phase 8 „Personen-Karte + Lightbox-Wissen-Tab".

### Deviations from plan
- Schreibverhalten von Auto-Write auf Bestätigungs-Liste umgestellt (User-Entscheidung
  2026-07-21, vor Phase 3 — siehe „Vorgeschichte" oben).
- `personen.yaml` nachträglich `private: true` gesetzt (User-Entscheidung vor Phase 4).
- `WizardTarget` erweitert um `entityId` (über die Phase-7-Planvorgabe hinaus, FINDINGS Phase 7).
- Phase 8: Lightbox-Aktionen navigieren nach `/wissen` statt Wizards inline zu duplizieren
  (Doppelpflege vermieden); alte Inline-`entity-wizard-dialog`-Lösung für „Wissen anlegen"
  entfernt (vestigial nach einem längst behobenen Routing-Guard-Bug). Details:
  `phase-8-personen-lightbox.md` → „Report-Back".
- P27-README: nur eine von zwei geplanten Amendment-Zeilen ergänzt (die andere war bereits
  seit Phase 1 inhaltsgleich vorhanden).
- Kein Datum („aktualisiert am") in Wissen-Detail/Übersicht — `EntityDto` hat keinen
  Zeitstempel, User-Entscheidung: weglassen statt Backend-Zusatzfeld (vor Phase 6).

### Follow-ups
- Phase 3 Parser-Trefferquote (5-10 Läufe gegen reale Personen) + Phase 4 API-Live-Smoke —
  warten auf ein gebundenes Gemma-Modell auf dieser Maschine.
- Bekannte Grenze aus Phase 7: Beziehungs-Chip-Navigation im Detail-Modal + danach geöffneter
  Wizard trifft noch die ursprüngliche statt der nachnavigierten Person.
- Bekannte Lücke aus Phase 6/8: „Web-Recherche starten" im leeren Detail-Zustand verknüpft die
  neu angelegte Entity nicht automatisch mit der Person (kein `media_links`-Prefill im
  Entity-Wizard) — Chip bleibt bis zur manuellen Verknüpfung auf „Wissen anlegen?" hängen.
- Volltext-Scraping der gefundenen Seiten (Feature-Radar-Punkt, bewusst draußen gelassen).
