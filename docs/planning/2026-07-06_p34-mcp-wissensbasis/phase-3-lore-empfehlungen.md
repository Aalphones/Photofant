# Phase 3 — Lore + Empfehlungen (read) + Korrektur-Patch

**Komplexität:** standard · **Unterbau:** P25, P26 · **Status:** pending

## Kontext (vor dem Bauen lesen)

- `README.md` + `phase-1` — Owner-Semantik (der `patch_entity`-Flow nutzt sie), Tool-Muster.
- `2026-07-01_p25-lore-panel/README.md` — Kontrakt: `get_lore(id)` voll,
  `GET /api/knowledge/lore?asset_id=|?person_id=`, `POST /api/knowledge/entities/{id}/patch`
  (field, value, reason).
- `2026-07-01_p26-recommendation-engine/README.md` — Kontrakt: `GET /api/recommendations?asset_id=`,
  `GET .../{source}/{target}/why-not`, Reason-Chain-Payload.
- Beim Umsetzen: realer `api/knowledge.py` (lore, patch) + `api/recommendations.py`.

## AK (falsifizierbar)

- [ ] In `mcp/tools/knowledge.py` ergänzt:
  - **Lore (read)**
    - [ ] `get_lore(asset_id? | person_id?)` → `GET /api/knowledge/lore`; gebündelte Sicht (Entity,
          Beziehungen mit aufgelösten Titeln, verwandte Medien, Quellen, Franchises). Kein Wissen →
          leeres Ergebnis, kein Fehler.
  - **Korrektur-Patch**
    - [ ] `patch_entity(id, field, value, reason)` → `POST /api/knowledge/entities/{id}/patch`,
          `owner` = `mcp.knowledge_owner`; läuft durch Validator + Ownership (P25-PatchJob-Pfad), erzeugt
          Explainability-Eintrag. Kein Gate (Ownership schützt, Vault-Changelog dokumentiert).
  - **Empfehlungen (read)**
    - [ ] `get_recommendations(asset_id)` → `GET /api/recommendations`; Vorschaubild-Referenz, Score,
          Reason-Chain. Fehlt der Cache → der Endpoint plant den Job, Tool meldet „wird berechnet".
    - [ ] `explain_recommendation(source_asset_id, target_asset_id)` → `GET .../{source}/{target}/why-not`.
- [ ] Lore/Empfehlungen sind read-only; nur `patch_entity` schreibt (über den geschützten Pfad).

## Umsetzung — Checkliste

- [ ] Lore-, Patch- und Recommendation-Tools in `mcp/tools/knowledge.py`.
- [ ] `get_recommendations`: „wird berechnet"-Fall sauber melden (der Agent kann später erneut fragen).
- [ ] Doc: `docs/routes.md` MCP-Wissens-Abschnitt ergänzen.

## Report-Back
