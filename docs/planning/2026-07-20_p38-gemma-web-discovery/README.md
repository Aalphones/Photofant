# P38 — Gemma Web-Discovery (öffentliche Entitäten automatisch anreichern)

> Baut auf P27 (Gemma-Integration, noch nicht archiviert — Smoke steht aus) und erweitert dessen
> Capability-Layer (ADR-027/028) um eine vierte Fähigkeit: **Web-Recherche mit Auto-Write** für
> öffentliche (nicht-private) Entitäten. *(private, lean — Vollplan, da neue Architektur:
> neues Tool, neuer Job, ADR-Amendment.)*

## Phasen
| # | Phase | Komplexität | Status |
|---|---|---|---|
| 1 | Fundament — Web-Search, Capability, Settings, ADR-031 | heikel | pending |
| 2 | KnowledgeDiscoveryJob (Suche → Gemma → Auto-Write) | heikel | pending |
| 3 | API-Route + Autonomie-/Privat-Guard | standard | pending |
| 4 | Frontend — Recherchieren-Button, Erklär-Dialog, Ergebnis-UI | standard | pending |

## Ziel
Für eine bestehende **öffentliche** Entity (z.B. Schauspieler:in) lässt sich per Klick eine
Web-Recherche auslösen: Gemma bekommt echte Suchergebnisse als Kontext, erweitert die
Beschreibung und schlägt neue verknüpfte Entitäten vor (Filme, in denen die Person mitspielte;
Wohnorte etc.). Anders als alle bisherigen P27-Funktionen schreibt dieser Pfad **ohne
Bestätigung** — das ist eine bewusste, hier explizit dokumentierte Ausnahme von der P27-
Kernregel „Gemma ändert nie direkt Daten" (ADR-006), siehe ADR-031.

## Vorgeschichte — was der User explizit entschieden hat
1. **Web-Zugriff:** Opt-in pro Aktion. Kein Hintergrund-/Auto-Trigger — Websuche läuft
   ausschließlich, wenn der User an einer konkreten Entity auf „Recherchieren" klickt.
2. **Schreibverhalten:** Automatisches Schreiben ohne Bestätigung — **nur für diese neue
   Funktion**. Sichtbar im Changelog, rückrollbar (Owner `web`, überschreibt nie `user`/`manual`-
   Werte, siehe unten). Alle bestehenden P27-Flows (Wizard-Vorschlag, Korrektur-Vorschlag,
   Interview-Anlage) bleiben unverändert bestätigungspflichtig.
3. **Private Entitäten:** kein neuer Ergänzen-Weg nötig — geprüft (`lore-panel.ts`), das
   bestehende „Ergänzen (KI)" aus P27 Phase 3 ist bereits webfrei und läuft schon heute
   uneingeschränkt auch auf privaten Entitäten (kein ADR-009-Konflikt, da kein Web-Zugriff).
   Punkt 2 aus der ursprünglichen Anfrage ist damit **bereits erledigt** — nichts zu bauen,
   nur zu verifizieren (Smoke-Punkt unten).

## Wichtiger Fund vor dem Planen — spart eine ganze Phase
`inference/tools.py` (`ToolRegistry`) ist laut Code-Map **unbenutztes Scaffolding** — die
bestehenden Jobs (`knowledge_import_job.py`, `knowledge_update_job.py`) rufen `generate()`
und `KnowledgeService` direkt auf, kein Tool-Routing, kein Agenten-Loop mit Funktionsaufrufen.
Es gibt in der ganzen Codebase noch **keine** Infrastruktur, in der Gemma selbst entscheidet,
wann sie ein Tool aufruft. Eine echte agentische Suche (Gemma entscheidet mitten in der
Generierung „ich suche jetzt") wäre ein komplett neuer, riskanter Baustein (Function-Calling-
Parsing, Retry-Logik, Multi-Turn-Loop) — dafür gibt's keinen Bedarf. Stattdessen: **derselbe
deterministische Single-Shot-Stil wie die bestehenden Jobs** — die Suche läuft **vor** dem
Gemma-Call (Python-Code entscheidet die Suchanfrage), die Ergebnisse werden als Kontext in
den Prompt gepackt, Gemma liefert einen strukturierten Text zurück, der geparst wird. Kein
Tool-Registry-Eintrag nötig (`ToolRegistry` bleibt unangetastet — dieselbe Direktaufruf-
Konvention wie die bestehenden Jobs).

Zweiter Fund: **`Owner.WEB`** existiert bereits im Schema (`knowledge/schema.py`), inklusive
korrekt gesetzter Überschreib-Priorität (`web` darf `inferred` überschreiben, nie `user`/
`manual`) und ist im Frontend-Typ (`OWNERS`) bereits mitgeführt. `Entity.sources: list[str]`
und die Lore-Panel-„Quellen"-Sektion existieren ebenfalls schon und rendern jede Liste
automatisch. Diese Funktion wurde offensichtlich schon in P22/P25 architektonisch
vorgedacht, nur nie geschrieben — das Fundament ist da, das senkt das Risiko dieses Plans
erheblich.

## Kontrakt (Backend ↔ Frontend)

- **Neue Capability:** `Capability.KNOWLEDGE_DISCOVERY = "knowledge_discovery"` (`inference/capabilities.py`).
- **Neuer Job-Kind:** `JobKind.KNOWLEDGE_DISCOVERY = "knowledge_discovery"` (`jobs/queue.py` Backend, `JOB_KINDS`-Array Frontend `models/job.model.ts`).
- **Neue Route:** `POST /api/knowledge/ai/discovery` · Body `{ entity_id: string }` · Response `{ job_id: string }`. 409 wenn `ai.autonomy.discovery != "auto"`, 422 wenn die Ziel-Domäne privat ist (ADR-009-Guard, wie `import-suggestion`).
- **Job-Ergebnis** (`JobDto.result` des `knowledge_discovery`-Jobs):
  ```ts
  interface KnowledgeDiscoveryResult {
    written_fields: string[];       // z.B. ["body"] oder []
    created_entities: { id: string; title: string; type: string }[];
    sources: string[];              // alle verwendeten URLs
    errors: string[];               // übersprungene/abgelehnte Einzel-Vorschläge, informativ
    explainability: { model_id: string; capability: string; prompt_version: string; duration_ms: number; confidence: number | null; reason: string };
  }
  ```
- **Autonomie-DTO erweitert:** `AutonomyDto` bekommt Feld `discovery: string` (Werte `"off"|"auto"`, kein `"ask"` — hier gibt's nichts zu bestätigen).

## Finale AK (Gesamt)
- [ ] Auf einer **öffentlichen** Entity im Lore Panel löst „Recherchieren" eine echte Websuche aus (sichtbar im Job-Dock), Gemma erweitert Beschreibung + schlägt neue verknüpfte Entitäten vor — **ohne Bestätigungs-Dialog**, das Ergebnis steht danach direkt im Markdown.
- [ ] Neue/erweiterte Felder tragen `owner: web`; ein bereits `user`/`manual`-owned Feld wird nie überschrieben (bestehende `owner_can_overwrite`-Regel greift unverändert).
- [ ] Jede Web-Schreibung erzeugt einen Changelog-Eintrag (sichtbar über „Warum geändert?") und trägt die verwendeten Quell-URLs in `entity.sources`.
- [ ] Auf einer **privaten** Entity wird „Recherchieren" gar nicht erst angeboten (Frontend) und die Route lehnt mit 422 ab (Backend-Guard, Verteidigung in der Tiefe).
- [ ] `ai.autonomy.discovery` steuert die Funktion global ab-/anschaltbar (Default `off` — Websuche + Auto-Write ist ein bewusster Opt-in, kein Default-Verhalten).
- [ ] Erstnutzung zeigt eine einmalige Erklärung („schreibt automatisch, ohne Rückfrage") — Idiotensicherheits-Gate, kein wiederholtes Genöle bei jedem Klick.
- [ ] Smoke bestätigt zusätzlich: das bestehende „Ergänzen (KI)" funktioniert bereits heute auf privaten Entitäten (keine neue Arbeit, nur Verifikation).

## Risiken
- 🟡 **Halluzinierte Fakten ohne Bestätigung** — das ist die bewusst akzeptierte Kernabweichung von ADR-006 (User-Entscheidung, siehe oben). Mitigation: nur `owner=web` (niedrigste Priorität außer `inferred`, jederzeit von `user`/`manual` überschreibbar), Changelog macht jede Änderung sichtbar/nachvollziehbar, `sources` macht die Herkunft transparent.
- 🟡 **Kleines lokales Modell (4B/12B) parst Suchergebnisse unzuverlässig** — Freitext-Parsing statt striktem JSON (robuster bei kleinen Modellen), defensiver Parser degradiert auf „nur Beschreibung, keine neuen Entitäten" statt zu crashen. Konkreter Check bei der Umsetzung: Phase 2, Abschnitt „Parser-Test".
- 🟡 **Web-Suchpaket-API kann sich ändern** (`ddgs`, kein offizieller SLA) — Phase 1 verifiziert die aktuelle API-Form gegen die installierte Version, bevor der Rest darauf aufbaut.
- 🟡 **Duplikat-Entitäten** — Namensgleichheit ist der einzige Dedup-Check (kein Fuzzy-Matching in v1). Bekannte Grenze, dokumentiert statt versteckt.

## Bewusst draußen (Feature-Radar, max. 1 Punkt — hier verbraucht)
**Volltext-Scraping der gefundenen Seiten** (statt nur Titel/Snippet aus der Suche) würde die
Qualität der Vorschläge deutlich heben, braucht aber einen HTML-Boilerplate-Extractor und mehr
Netzwerk-Zeit pro Klick. Backlog-Kandidat für eine spätere Phase, kein Blocker für v1 — sag
Bescheid, falls das jetzt schon mit rein soll, sonst bleibt's bei Snippet-only.

## Konfidenz-Ausweis
Am unsichersten: **wie zuverlässig ein 4B/12B-Modell das vorgeschriebene Ausgabeformat
(`### BESCHREIBUNG` / `### NEUE_ENTITAETEN` / `### QUELLEN`) tatsächlich einhält** — die Alt-
Jobs prüfen nur „ist die Antwort leer", nicht Format-Treue. Check: in Phase 2 nach der ersten
echten Generierung 5-10 Testläufe mit unterschiedlichen realen Personen fahren und die
Trefferquote des Parsers protokollieren, bevor Phase 3/4 draufbauen. Zweite Unsicherheit:
`ddgs`-Paketname/API — Check: `uv pip show ddgs` + ein Interaktions-Test in Phase 1, bevor
der Rest des Plans darauf aufbaut.

## Smoke-Checkliste (du prüfst am Plan-Ende)
Wackelstellen zuerst (Konfidenz-Ausweis oben):
1. **Parser-Robustheit:** 3-5 „Recherchieren"-Läufe auf verschiedenen realen, bekannten
   öffentlichen Personen → Ergebnis-Panel zeigt jedes Mal etwas Sinnvolles (nicht leer, nicht
   kaputt), auch wenn Gemma mal vom Format abweicht.
2. **Kein Auto-Trigger:** `ai.autonomy.discovery` bleibt nach Neuinstallation/Zurücksetzen auf
   `off` — der Button ist nirgends sichtbar, ohne dass du ihn manuell aktivierst.
3. **User-Werte bleiben unantastbar:** Ein Feld, das du zuvor manuell korrigiert hast
   (`owner=user`), wird durch „Recherchieren" **nicht** überschrieben — nur unbeschriebene
   oder `web`/`inferred`-Felder ändern sich.
4. **Private Entität geschützt:** Auf einer privaten Person taucht der Button nirgends auf,
   ein direkter API-Aufruf (falls du curl/Postman nutzt) liefert 422.
5. **Bestehendes „Ergänzen (KI)" auf privaten Entitäten:** einmal testen, dass das (bereits
   heute existierende, webfreie) „Ergänzen (KI)" auf einer privaten Person weiterhin
   funktioniert — reine Verifikation, keine neue Funktion.
6. **Changelog + Quellen sichtbar:** nach einem erfolgreichen Lauf zeigt „Warum geändert?" den
   neuen Eintrag, die „Quellen"-Sektion listet die verwendeten URLs.

## Bottom-Sektionen
_(beim Archivieren füllen)_

### Summary
### Files touched
### Commits
### Deviations from plan
### Follow-ups
