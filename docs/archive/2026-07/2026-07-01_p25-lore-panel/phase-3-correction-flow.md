# Phase 3 — Korrektur-Flow („Das stimmt nicht" → PatchJob)

**Komplexität:** standard · **Status:** complete

## Kontext
- README → Kontrakt (`PatchJob`, Patch-REST, Explainability)
- Konzept Dok 050 §7, Dok 020 §13/§14 · **P22** (`update_entity`, Validator, Ownership)
- Bestand: `jobs/queue.py`, `jobs/*_job.py`, `api/knowledge.py` · Phase 1/2: Lore-API, Panel

## AK
- [x] Jede auto/inferred-Info im Panel hat dezente „Das stimmt nicht"-Aktion → Formular (neuer Wert + Grund).
  **Scope-Deviation:** MVP deckt die Kurzbio (`body`) ab — das prominenteste Freitext-Feld im
  Panel. Backend/Job/Route sind feldgenerisch (`PATCHABLE_FIELDS`), Erweiterung auf weitere
  Felder (z.B. einzelne Beziehungen) ist reine UI-Arbeit, kein neuer Pfad — bewusst nicht in
  dieser Phase, um den Umfang nicht zu sprengen (kein Beleg im Konzept für „jedes Feld einzeln").
- [x] Absenden → `POST .../{id}/patch` → `PatchJob` → Validator → `update_entity(owner=user)` → Markdown + Cache aktualisiert.
- [x] Panel zeigt neuen Wert ohne manuellen Datei-Reload; Nutzer hat keine Datei angefasst.
  (Läuft über SSE-Job-Warte + Lore-Reload, kein Lightbox-Reload nötig.)
- [x] Änderung erzeugt Explainability-Eintrag (Grund, Quelle=user, Zeit, Job).
- [x] Ownership: user-Patch überschreibt inferred/web-Werte.

## Umsetzung
- [x] `jobs/knowledge_patch_job.py` + Registrierung (`JobKind.KNOWLEDGE_PATCH`)
- [x] Patch-Route in `api/knowledge.py` (`POST /entities/{id}/patch`, 422 bei unbekanntem Feld vorab)
- [x] Explainability-Persistenz: **Cache-Tabelle** `knowledge_changelog` (`ChangelogService`),
  nicht Vault-Changelog — gleiche Begründung wie `knowledge_tasks` (P23): Arbeitszustand/
  Metadaten, die die UI abfragen/joinen muss, kein Vault-Wissen; ein Markdown-Anhang wäre
  nicht strukturiert lesbar. `GET /entities/{id}/changelog` legt sie offen (geteilte Payload P26).
- [x] UI: „Das stimmt nicht" + Korrektur-Formular im Panel (Kurzbio, siehe Scope-Deviation oben)
- [x] Doc: `docs/routes.md`, `docs/code-map.md`
- [x] **Gesamt-P25:** finale AK + Smoke-Checkliste der README gegenprüfen — **danach MVP erreicht**
