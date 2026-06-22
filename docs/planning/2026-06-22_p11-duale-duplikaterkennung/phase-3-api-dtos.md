# Phase 3 — API-Kontrakt (DTOs)

**Tier:** standard  
**Status:** pending

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

- [ ] `review.py DupePairDto` hat alle Kontrakt-Felder: `phash_distance`, `phash_similarity_pct`, `clip_distance`, `clip_similarity_pct`, `triggered_by`
- [ ] `duplicates.py DupePairDto` ebenso (ohne `id`, `asset_a/b`, `created_at` — Person-Search-Dto bleibt schlanker)
- [ ] `triggered_by` ist `"phash" | "clip" | "both"` — kein weiterer Wert möglich
- [ ] `similarity_pct` in `duplicates.py` zeigt das **Maximum** aus DHash- und CLIP-Similarity
- [ ] Alle Felder die nullable sind korrekt als `int | None` bzw. `float | None` typisiert
- [ ] `GET /duplicates/search` akzeptiert neuen Body-Parameter `clip_threshold: float` (Default aus Settings)
- [ ] Bestehende Clients (ohne `clip_threshold`) brechen nicht — default greift

---

## Checkliste

### review.py

- [ ] `DupePairDto` erweitern:
  ```python
  phash_distance:       int | None
  phash_similarity_pct: int | None
  clip_distance:        float | None
  clip_similarity_pct:  int | None
  triggered_by:         Literal["phash", "clip", "both"]
  ```
- [ ] `_to_pair_dto` anpassen — berechnet `phash_similarity_pct`, `clip_similarity_pct`, `triggered_by` aus DB-Werten
  ```python
  triggered_by = (
      "both"  if item.phash_distance is not None and item.clip_distance is not None else
      "phash" if item.phash_distance is not None else
      "clip"
  )
  ```
- [ ] `SimilarAssetDto` erweitern: `clip_distance: float | None`, `clip_similarity_pct: int | None`

### duplicates.py

- [ ] `DupeSearchRequest` um `clip_threshold: float = _DEFAULT_CLIP_THRESHOLD` erweitern
- [ ] Konstante `_DEFAULT_CLIP_THRESHOLD = 0.15` und `_MIN_CLIP_THRESHOLD = 0.05` anlegen
- [ ] `_MAX_THRESHOLD = 32` bleibt für DHash
- [ ] `DupePairDto` in `duplicates.py` erweitern (analog review.py, ohne Review-spezifische Felder)
- [ ] `search_person_duplicates`: CLIP-Vergleich zusätzlich zum DHash laufen lassen
  - CLIP nur wenn `dupe_clip_enabled` in Settings
  - Embeddings aller Person-Assets laden, paarweise vergleichen (inline, kein Job-Chunk nötig — wenige Bilder pro Person)
  - Ergebnis: UNION der beiden Listen, `triggered_by` berechnen
- [ ] `similarity_pct` = `max(phash_sim, clip_sim)` (whichever is not None)

---

## Report-Back

_Hier trägt der Umsetzer nach Abschluss ein was abwich oder auffiel._
