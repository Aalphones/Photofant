# P23 — Knowledge Wizard (MVP, ohne KI)

> Roadmap-Phase 2 (Dok 030 §13, Dok 050 §4/§11/§12). **Erste UI der Wissensbasis.** Baut auf **P22** auf. Keine KI — manueller Dialog; Gemma ersetzt ihn später (**P27**), Struktur bleibt. *(private, lean.)*

## Ziel
Wissen ohne KI aufbauen: eine Aufgaben-Queue sammelt „hier fehlt Wissen", ein Wizard legt daraus manuell eine Entity an (→ Markdown im Vault), der Nutzer sieht offene Aufgaben gesammelt und arbeitet sie ab.

## Scope
**Drin:** `knowledge_tasks` + Service + REST · `KnowledgeLookupJob` (ohne KI, Trigger-Anbindung erst in P24, hier manuell auslösbar) · Wizard-Dialog (Entity manuell) · Work-Queue-Sicht (Dok 050 §12).
**Draußen:** KI-Ausfüllen/Interview → **P27** · Auto-Trigger aus Ereignissen → P24 · Webrecherche → später.

## Abhängigkeiten
**P22** (Service, REST, Vault, Cache). Frontend legt den in P22 reservierten Kontrakt real an: `models/knowledge.model.ts`, `store/knowledge/`, `services/knowledge.service.ts`, `features/wissen/`.

## Kontrakt-Ergänzungen
- **`knowledge_tasks`** (eigene Migration): `id`, `kind` (new_person|missing_entity|confirm_relationship|review_recommendation), `status` (open|resolved|dismissed), `context` (JSON, z.B. person_id), `created_at`, `resolved_at`. Arbeitszustand, kein Vault-Wissen.
- **REST:** `GET /api/knowledge/tasks?status=` · `POST .../tasks` · `POST .../tasks/{id}/resolve` · `.../dismiss`.
- **Job:** `jobs/knowledge_lookup_job.py` — bei fehlender Entity eine Aufgabe anlegen, idempotent (Dedup über `context`).

## Reservierte Settings
`knowledge.autoLookup` (bool, Default true; ADR-008: abschaltbar) — greift real mit P24-Triggern.

## Design-Lage (freihändig nach Konzept — freigegeben)
Kein Mockup. UI-Struktur unten als AK fixiert (Dok 050 §4/§12), am Bestand (Tailwind-Tokens, `ui/*-dialog/`) ausgerichtet. Ruhig, kein Chat (Dok 050 §13).

## Phasen
| # | Phase | Komplexität | Status |
|---|---|---|---|
| 1 | Task-Queue (Backend) | standard | complete |
| 2 | Wizard-UI (Entity manuell anlegen) | standard | pending |
| 3 | Work-Queue-UI (offene Aufgaben) | standard | pending |

Backend zuerst, dann UI (2 vor 3, gemeinsame Store-Slice).

## Finale AK (Gesamt)
- [ ] Nutzer legt per Wizard eine vollständige Entity an (Typ, Titel, Aliase, Domäne, Beschreibung, ≥1 Beziehung); danach existiert die Markdown-Datei.
- [ ] Offene Aufgaben gesammelt sichtbar; Erledigen öffnet den Wizard, markiert die Aufgabe nach Anlegen als erledigt.
- [ ] Erstnutzer versteht die UI ohne Doku (klare Labels, Beispiel-Placeholder, optionale i-Erklärungen).
- [x] `KnowledgeLookupJob` legt bei fehlender Entity genau eine Aufgabe an (idempotent).

## Smoke-Checkliste (du prüfst am Plan-Ende)
1. „Wissen" in der Nav öffnen → Wizard → Entity anlegen → Datei liegt im Vault.
2. Aufgabe per `curl POST .../tasks` anlegen → erscheint in der Work-Queue.
3. Aufgabe „Erledigen" → Wizard vorbelegt → speichern → Aufgabe verschwindet.
4. Zweiter Lookup zum selben Kontext → keine zweite Aufgabe.

## Risiken
- 🟡 **Wizard-Überladung** → nur Pflicht (Typ, Titel) prominent, Rest optional/eingeklappt; Beziehungen per Auto-Complete.
- 🟡 **Aufgaben-Duplikate** → Lookup idempotent über `context`.
- 🟡 **Store-Kollision Phase 2/3** → Phase 2 legt Slice-Struktur an, Phase 3 erweitert nur.

## Chesterton
Neuer Feature-Ordner + Tabelle + Job, additiver Nav-Eintrag „Wissen". Kein Ersetzen.

---
## Summary / Deviations / Follow-ups
_(beim Archivieren)_ — Follow-up: Interview-Mode / KI-Ausfüllen → P27.
