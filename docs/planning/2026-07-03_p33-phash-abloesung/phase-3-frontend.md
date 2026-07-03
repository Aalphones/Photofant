# Phase 3 — Frontend-Anpassung

**Komplexität:** mechanisch · **Status:** pending

## Kontext (vor Arbeitsbeginn lesen)

- `README.md` dieses Plans (Kontrakt-Sektion — die DTO-Änderungen sind der Maßstab)
- Modelle: `frontend/src/app/models/review.model.ts`, `person.model.ts`, `collection.model.ts`, `config.model.ts` (PROCESSING_CONFIG_DEFAULTS)
- Services: `frontend/src/app/services/person.service.ts` (`searchDuplicates`)
- Store: `frontend/src/app/store/review/review.reducer.ts`, `frontend/src/app/store/models/models.effects.ts` (Settings-Key-Mapping Z. ~22–48)
- UI: `frontend/src/app/features/review/review-dupes/` (`dupe-pair-row/`, `dupe-compare/`), `features/personen/dupe-check-dialog/`, `ui/rerun-dialog/`, `features/einstellungen/verarbeitung/`, `features/trainingssets/training-set-dupes/`
- `docs/conventions/angular.md`, `docs/conventions/typescript.md`, `docs/conventions/ngrx.md`

## AK

1. `npm run lint && npm run build` grün; kein `phash`/`triggeredBy`-Vorkommen mehr unter `frontend/src/`.
2. Review-Dupes, Personen-Dupe-Check und Trainingsset-Dupes zeigen Ähnlichkeit ausschließlich als CLIP-% an.
3. Rerun-Dialog bietet keinen pHash-Schritt mehr; Einstellungen → Verarbeitung ohne pHash-Toggle/-Schwelle.
4. Trainingsset-Dupes-Schwellen-Control arbeitet in %-Semantik (mappt auf CLIP-Distanz), mit dezenter optionaler Erklärung (Tooltip/i-Icon) was „Ähnlichkeit" hier heißt.

## Checkliste

- [ ] **Modelle:** `phash_distance`/`phashDistance`, `phash_similarity_pct`, `triggered_by` aus `review.model.ts`, `person.model.ts` (`PersonDupePair`), `collection.model.ts` (`CollectionDupePair`: `clip_distance: number`); `dupeThreshold` + `dupePhashEnabled` aus `config.model.ts`-Typ und `PROCESSING_CONFIG_DEFAULTS`.
- [ ] **`person.service.ts`:** `searchDuplicates(personId, clipThreshold)` — pHash-Threshold-Param + Body-Feld `threshold` raus.
- [ ] **`models.effects.ts`:** Mapping-Zeilen `dupeThreshold`/`dupePhashEnabled` raus (beide Richtungen: Key-Map + Parse-Block).
- [ ] **Review-Dupes-UI:** `dupe-pair-row.html` — pHash-Spalte/Badge und `triggered_by`-Anzeige raus, nur noch Ähnlichkeit %; `dupe-compare.ts` analog (Felder + Template).
- [ ] **`dupe-check-dialog`** (Personen): pHash-Anzeige/-Parameter raus, nur CLIP-%.
- [ ] **`rerun-dialog.ts`:** „pHash"-Step-Option (Checkbox/Eintrag) entfernen.
- [ ] **Einstellungen → Verarbeitung:** pHash-Toggle + alte Schwelle aus Template/Component; CLIP-Toggle wird als „Duplikaterkennung" beschriftet (Master-Toggle laut Kontrakt) — Tooltip-Text entsprechend anpassen.
- [ ] **Trainingsset-Dupes:** Threshold-Control von Hamming (0–64) auf %-Slider umstellen (UI zeigt „Ähnlichkeit ≥ X %", Request sendet `1 - X/100` als CLIP-Distanz); i-Icon/Tooltip: „100 % = praktisch identisch, 95 % = sehr ähnlich".
- [ ] **Abschluss:** `grep -ri "phash\|triggeredBy" frontend/src/` → 0 Treffer; `npm run lint && npm run build`.

## Report-Back
