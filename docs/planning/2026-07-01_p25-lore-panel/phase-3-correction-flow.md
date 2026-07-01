# Phase 3 — Korrektur-Flow („Das stimmt nicht" → PatchJob)

**Komplexität:** standard · **Status:** pending

## Kontext
- README → Kontrakt (`PatchJob`, Patch-REST, Explainability)
- Konzept Dok 050 §7, Dok 020 §13/§14 · **P22** (`update_entity`, Validator, Ownership)
- Bestand: `jobs/queue.py`, `jobs/*_job.py`, `api/knowledge.py` · Phase 1/2: Lore-API, Panel

## AK
- [ ] Jede auto/inferred-Info im Panel hat dezente „Das stimmt nicht"-Aktion → Formular (neuer Wert + Grund).
- [ ] Absenden → `POST .../{id}/patch` → `PatchJob` → Validator → `update_entity(owner=user)` → Markdown + Cache aktualisiert.
- [ ] Panel zeigt neuen Wert ohne manuellen Datei-Reload; Nutzer hat keine Datei angefasst.
- [ ] Änderung erzeugt Explainability-Eintrag (Grund, Quelle=user, Zeit, Job).
- [ ] Ownership: user-Patch überschreibt inferred/web-Werte.

## Umsetzung
- [ ] `jobs/knowledge_patch_job.py` + Registrierung
- [ ] Patch-Route in `api/knowledge.py`
- [ ] Explainability-Persistenz (Feld, alt→neu, Grund, Quelle, Zeit, Job) — Ort (Vault-Changelog vs. Cache-Tabelle) begründen
- [ ] UI: „Das stimmt nicht" + Korrektur-Formular im Panel
- [ ] Doc: `docs/routes.md`, `docs/code-map.md`
- [ ] **Gesamt-P25:** finale AK + Smoke-Checkliste der README gegenprüfen — **danach MVP erreicht**
