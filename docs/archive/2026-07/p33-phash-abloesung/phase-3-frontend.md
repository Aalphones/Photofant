# Phase 3 — Frontend-Anpassung

**Komplexität:** mechanisch · **Status:** complete

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

- [x] **Modelle:** `phash_distance`/`phashDistance`, `phash_similarity_pct`, `triggered_by` aus `review.model.ts`, `person.model.ts` (`PersonDupePair`), `collection.model.ts` (`CollectionDupePair`: `clip_distance: number`); `dupeThreshold` + `dupePhashEnabled` aus `config.model.ts`-Typ und `PROCESSING_CONFIG_DEFAULTS`.
- [x] **`person.service.ts`:** `searchDuplicates(personId, clipThreshold)` — pHash-Threshold-Param + Body-Feld `threshold` raus.
- [x] **`models.effects.ts`:** Mapping-Zeilen `dupeThreshold`/`dupePhashEnabled` raus (beide Richtungen: Key-Map + Parse-Block).
- [x] **Review-Dupes-UI:** `dupe-pair-row.html` — pHash-Spalte/Badge und `triggered_by`-Anzeige raus, nur noch Ähnlichkeit %; `dupe-compare.ts` analog (Felder + Template).
- [x] **`dupe-check-dialog`** (Personen): pHash-Anzeige/-Parameter raus, nur CLIP-%.
- [x] **`rerun-dialog.ts`:** „pHash"-Step-Option (Checkbox/Eintrag) entfernen.
- [x] **Einstellungen → Verarbeitung:** pHash-Toggle + alte Schwelle aus Template/Component; CLIP-Toggle wird als „Duplikaterkennung" beschriftet (Master-Toggle laut Kontrakt) — Tooltip-Text entsprechend angepasst.
- [x] **Trainingsset-Dupes:** Threshold-Control von Hamming (0–64) auf %-Slider umstellen (UI zeigt „Ähnlichkeit ≥ X %", Request sendet `1 - X/100` als CLIP-Distanz); i-Icon/Tooltip: „100 % = praktisch identisch, 95 % = sehr ähnlich".
- [x] **Abschluss:** `grep -ri "phash\|triggeredBy" frontend/src/` → 0 Treffer; `npm run lint && npm run build`.

## Report-Back

**Deviation (Chesterton's Fence, siehe FINDINGS.md → Phase 4):** Grep fand pHash-Reste
über die im Kontext gelistete Datei-Auswahl hinaus: `asset.model.ts`/`lightbox.ts`/`lightbox.html`
(`has_phash`/`hasPHash`-Gate am „Ähnliche Bilder"-Button, `phash_distance` in `SimilarAsset`)
und `classify.service.ts` (`ClassifyStep`-Literal `'phash'`). Phase-3-AK1 verlangt explizit
„kein phash-Vorkommen mehr unter frontend/src/" — das schließt diese Stellen mit ein.

Dabei aufgefallen: `AssetDto.has_phash` (Backend `api/assets.py`) lieferte seit Phase 1
für jedes neu importierte Bild `false` (Embedding-Job schreibt kein `phash` mehr) — der
„Ähnliche Bilder"-Button war seither für neue Assets unbemerkt tot. Backend-Feld auf
`has_embedding` (`asset.clip_embedding is not None`) umgestellt, inkl. Batch-Query in
`list_assets` (die Spalte ist `deferred` — ein Pro-Zeile-Zugriff hätte in der Galerie-Liste
N+1-Extra-Queries ausgelöst). Bestehender Test `test_assets_search.py` (6 Tests, deckt
`list_assets` ab) lief grün.

`DupePair`/`PersonDupePair`/`CollectionDupePair`: `clip_distance`/`clip_similarity_pct` von
`number | null` auf `number` (non-null) verschärft, da Backend das laut Kontrakt garantiert —
deckt auch tote Downstream-Logik auf (z.B. `bestDistance`-pHash-Normalisierung im Reducer,
die nie mehr etwas zu normalisieren hatte).
