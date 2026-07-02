# Phase 3 — API-Kontrakt (DTOs)

**Tier:** standard  
**Status:** complete

---

## Kontext (was vorher lesen)

- `backend/photofant/api/review.py` — `DupePairDto`, `SimilarAssetDto`, `_to_pair_dto`
- `backend/photofant/api/duplicates.py` — `DupePairDto` (anderes DTO gleicher Name!), `search_person_duplicates`
- Kontrakt-Sektion in README — gibt die genauen Felder vor
- Phase 1 + 2 müssen abgeschlossen sein

Achtung: `review.py` und `duplicates.py` haben beide ein eigenes `DupePairDto` — unterschiedliche
Felder, gleicher Name. Nicht verwechseln; sie bleiben getrennte Modelle.

---

## Abnahme-Kriterien

- [x] `review.py DupePairDto` hat alle Kontrakt-Felder: `phash_distance`, `phash_similarity_pct`, `clip_distance`, `clip_similarity_pct`, `triggered_by`
- [x] `duplicates.py DupePairDto` ebenso (ohne `id`, `asset_a/b`, `created_at` — Person-Search-Dto bleibt schlanker)
- [x] `triggered_by` ist `"phash" | "clip" | "both"` — kein weiterer Wert möglich
- [x] `similarity_pct` in `duplicates.py` zeigt das **Maximum** aus DHash- und CLIP-Similarity
- [x] Alle Felder die nullable sind korrekt als `int | None` bzw. `float | None` typisiert
- [x] `POST /duplicates/search` akzeptiert neuen Body-Parameter `clip_threshold: float` (Default aus Settings)
- [x] Bestehende Clients (ohne `clip_threshold`) brechen nicht — default greift

---

## Checkliste

### review.py

- [x] `DupePairDto` erweitern:
  ```python
  phash_distance:       int | None
  phash_similarity_pct: int | None
  clip_distance:        float | None
  clip_similarity_pct:  int | None
  triggered_by:         Literal["phash", "clip", "both"]
  ```
- [x] `_to_pair_dto` anpassen — berechnet `phash_similarity_pct`, `clip_similarity_pct`, `triggered_by` aus DB-Werten
  ```python
  triggered_by = (
      "both"  if item.phash_distance is not None and item.clip_distance is not None else
      "phash" if item.phash_distance is not None else
      "clip"
  )
  ```
- [x] `SimilarAssetDto` erweitern: `clip_distance: float | None`, `clip_similarity_pct: int | None`

### duplicates.py

- [x] `DupeSearchRequest` um `clip_threshold: float = _DEFAULT_CLIP_THRESHOLD` erweitern
- [x] Konstante `_DEFAULT_CLIP_THRESHOLD = 0.15` und `_MIN_CLIP_THRESHOLD = 0.05` anlegen
- [x] `_MAX_THRESHOLD = 32` bleibt für DHash
- [x] `DupePairDto` in `duplicates.py` erweitern (analog review.py, ohne Review-spezifische Felder)
- [x] `search_person_duplicates`: CLIP-Vergleich zusätzlich zum DHash laufen lassen
  - CLIP nur wenn `dupe_clip_enabled` in Settings
  - Embeddings aller Person-Assets laden, paarweise vergleichen (inline, kein Job-Chunk nötig — wenige Bilder pro Person)
  - Ergebnis: UNION der beiden Listen, `triggered_by` berechnen
- [x] `similarity_pct` = `max(phash_sim, clip_sim)` (whichever is not None)

---

## Report-Back

- Zusätzlich `_MAX_CLIP_THRESHOLD = 0.30` angelegt (nicht explizit in der Checkliste, aber im README-Kontrakt als Range 0.05–0.30 vorgegeben) — clampt `clip_threshold` symmetrisch zum bestehenden DHash-Threshold-Clamp.
- Doku-Tippfehler behoben: AK sprach von `GET /duplicates/search`, die Route ist und bleibt `POST`.
- `search_person_duplicates` lädt jetzt auch Assets ohne `phash` (früher gefiltert) — nötig, damit CLIP-only-Treffer nicht durchs Query-Filter fallen.
- Sortierung von `duplicates.py`-Ergebnissen umgestellt: statt `phash_distance` aufsteigend jetzt `similarity_pct` absteigend (bester Treffer zuerst, methodenunabhängig).
