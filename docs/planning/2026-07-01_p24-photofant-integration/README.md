# P24 — Photofant-Integration (Bilder ↔ Wissen)

> Roadmap-Phase 3 (Dok 050 §4, Dok 030 §10). Verbindet Galerie und Wissensbasis. Baut auf **P22** + **P23** auf. Höchster Nutzermehrwert der Roadmap. *(private, lean.)*

## Ziel
Personen/Assets mit Entities verknüpfen; hat eine bestätigte Person keine Entity, entsteht automatisch eine Wissens-Aufgabe (→ Wizard). Verbindung wird an Person und Asset sichtbar. Aus „Gesicht #42" wird die Entity „Robert Downey Jr.".

## Scope
**Drin:** Person↔Entity + Asset↔Entity (nutzt `knowledge_media_links` aus P22) · REST zum Verknüpfen/Lösen · Job-Kette Person bestätigt → `KnowledgeLookupJob` (P23) → Aufgabe, mit Tiefen-/Schleifenschutz (Dok 030 §11) · „🆕 Neue Person erkannt"-Affordance · verknüpfte Entity an Personen-Karte + Asset-Detail.
**Draußen:** Lore-Darstellung → P25 · Empfehlungen → P26 · Web-Recherche → P27.

## Abhängigkeiten
**P22** (`link_media`, Media-Link-Tabelle) + **P23** (LookupJob, Task-Queue, `features/wissen/`). Berührt additiv: `store/persons/`, `features/personen/`, `features/review/`, `api/persons.py`.

## Kontrakt-Ergänzungen
- **REST:** `POST/DELETE /api/persons/{id}/link-entity` (body: entity_id) · analog `/api/assets/{id}/link-entity`. Intern via `KnowledgeService.link_media`.
- **Trigger:** bei „Person bestätigt" ohne verknüpfte Entity + `autoLookup` an → `KnowledgeLookupJob` mit `context={person_id}`. **Schleifenschutz:** `ParentJobId`/`Depth`, `jobs.maxDepth` (P22), idempotent (P23), kein Selbst-Typ-Recurse.
- **DTO:** Personen-/Asset-Detail bekommen optionales `linked_entity` (id, title, type) — read-only Cache-Projektion.

## Reservierte Entscheidungen & Settings
~~ADR-011 (intelligente Jobs, von P22 reserviert)~~ — Nummer war bei Umsetzung bereits an
`011-galerie-virtual-scroll.md` vergeben; real angelegt als **ADR-014**
(`docs/decisions/014-wissens-lookup-auto-trigger-ohne-tiefenschutz.md`). ~~Nutzt `knowledge.autoLookup`
(P23) + `jobs.maxDepth` (P22), keine neuen Keys~~ — beides existierte nicht, `knowledge.auto_lookup`
wurde als echtes neues Setting angelegt, `jobs.maxDepth` bewusst nicht gebaut (Details: ADR-014,
`FINDINGS.md`).

## Design-Lage (freihändig — freigegeben)
Kein Mockup. Affordance + Entity-Anzeige fügen sich in bestehende Screens (Personen-Karte, Review-Queue, Asset-Detail) — **Screen-Eigentümer-Regel:** in deren Struktur einbauen, kein Wegwerf-Container. Dezent, kein Popup-Zwang (Dok 050 §13).

## Phasen
| # | Phase | Komplexität | Status |
|---|---|---|---|
| 1 | Entity-Linking + Job-Kette (Backend) | standard | complete |
| 2 | „Neue Person erkannt"-Affordance (UI) | standard | complete |
| 3 | Verknüpfte Entity an Person/Asset (UI) | mechanisch | pending |

## Finale AK (Gesamt)
- [ ] Person mit Entity verknüpfbar + lösbar; überlebt Neustart (Cache + Vault media_links).
- [ ] Person bestätigt ohne Entity (+ Auto-Lookup) → **genau eine** Aufgabe, **ohne** Job-Endlosschleife (Depth-Schutz greift).
- [x] Neu erkannte Person → UI bietet dezent: Wissen anlegen / später / ignorieren.
- [ ] Verknüpfte Entity an Personen-Karte + Asset-Detail sichtbar, Klick → Wissens-Sicht.
- [ ] Bestehende Personen-/Review-Funktionen unverändert (keine Regression).

## Smoke-Checkliste (du prüfst am Plan-Ende)
1. `curl POST /api/persons/{id}/link-entity` → Personen-Detail zeigt `linked_entity`, überlebt Neustart.
2. Eine Person bestätigen, die keine Entity hat → genau eine offene Aufgabe entsteht, App hängt nicht in einer Job-Schleife (Job-Dock beobachten).
3. Neue Person im Review → Hinweis „Wissen anlegen" → Wizard → danach verknüpft, Hinweis weg.
4. Personen-Karte + Bild-Detail zeigen den Entity-Chip, Klick landet im Wissen.

## Risiken
- 🟡 **Job-Endlosschleife** (Dok 030 §11) → `ParentJobId`+`Depth`+`maxDepth`, kein Selbst-Typ, Idempotenz. **Der kritische Punkt dieses Plans.**
- 🟡 **Regression im Personen-Flow** (physische Ordner-Moves, Critical Rule 2) → Chesterton unten, Trigger nur additiv anhängen.
- 🟡 **Verwaiste Links** → Link-Löschung an Personen-Löschung koppeln; Reconcile (P22 Phase 4) räumt Cache-Waisen.

## Chesterton
**Vor Änderung verstehen:** der Personen-Bestätigungs-Pfad (`api/persons.py`, `jobs/clustering_job.py`/`face_job.py`, `media/person_folders.py`) verschiebt bei Bestätigung/Merge **physisch Bilddateien** in Personen-Ordner. P24 hängt **nur** einen Job-Trigger + optionales DTO-Feld an, ändert diesen Move-Pfad nicht. Beim Umsetzen den Einstiegspunkt lesen, bevor der Trigger gesetzt wird.

---
## Summary / Deviations / Follow-ups
_(beim Archivieren)_ — Follow-up: Auto-Web-Recherche verknüpfter Entities → P27.
