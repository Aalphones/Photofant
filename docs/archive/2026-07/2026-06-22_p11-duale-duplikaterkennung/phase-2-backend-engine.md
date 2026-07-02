# Phase 2 — Backend-Engine (Scan + Similar)

**Tier:** heikel  
**Status:** complete

---

## Kontext (was vorher lesen)

- `backend/photofant/jobs/dupe_scan_job.py` — aktueller Scan-Job, Chunking-Logik, `_insert_pairs`
- `backend/photofant/db/vector_index.py` — CLIP-Embeddings laden, `EMBEDDING_DIM = 768`
- `backend/photofant/media/phash.py` — `find_similar`, `hamming_distance`
- `backend/photofant/api/review.py` — `GET /assets/{id}/similar` (Lightbox-Endpunkt)
- Phase 1 muss abgeschlossen sein (Schema + Settings)
- Kontrakt in README (DB-Schema nach Migration)

---

## Abnahme-Kriterien

- [x] `run_dupe_scan_job` nutzt pHash wenn `dupe_phash_enabled` (distance == 0, kein Threshold), CLIP wenn `dupe_clip_enabled`
- [x] Ergebnis ist die Vereinigung (UNION) beider Methoden — kein Paar doppelt
- [x] Für CLIP-Paare: `phash_distance = NULL`, `clip_distance` gesetzt
- [x] Für DHash-Paare: `phash_distance` gesetzt, `clip_distance = NULL`
- [x] Für Paare die von beiden erkannt werden: beide Felder gesetzt
- [x] CLIP-Scan läuft in 1000er-Blöcken (Outer-Loop), bleibt unter 50 MB RAM-Peak pro Chunk
- [x] Assets ohne `clip_embedding` werden im CLIP-Scan übersprungen (kein Fehler)
- [x] `GET /assets/{id}/similar` (Lightbox) gibt CLIP-Treffer zurück wenn `dupe_clip_enabled` — ergänzt DHash-Treffer (UNION, nach Ähnlichkeit sortiert)
- [x] Beide Methoden deaktiviert → kein Scan / keine Similar-Results (kein Crash)

---

## Checkliste

### CLIP-Pairwise-Vergleich (Hilfsfunktion)

- [x] Neue Funktion `_compare_chunk_clip` in `dupe_scan_job.py` (analog zu `_compare_chunk`)
  ```python
  def _compare_chunk_clip(
      asset_embeddings: list[tuple[int, bytes]],  # (asset_id, blob)
      start: int,
      end: int,
      threshold: float,                            # Cosine-Distance
  ) -> list[tuple[int, int, float]]:              # (a_id, b_id, clip_distance)
  ```
- [x] Embeddings deserialisieren: `np.frombuffer(blob, dtype=np.float32)` (768-dim, bereits L2-normiert)
- [x] Chunk-Matrix `A = stack(embeddings[start:end])` (shape: chunk×768)
- [x] Rest-Matrix `B = stack(embeddings)` (shape: N×768)
- [x] `sims = A @ B.T` → Cosine-Similarity (da L2-normiert = Dot-Product)
- [x] `dists = 1.0 - sims` → Cosine-Distance
- [x] Pairs wo `dist ≤ threshold` und `i < j` sammeln (kein Selbst-Vergleich, kein Doppel)

### Scan-Job update

- [x] `run_dupe_scan_job`: Settings-Felder `dupe_phash_enabled`, `dupe_clip_enabled`, `dupe_clip_threshold` laden
- [x] pHash-Pfad nur ausführen wenn `dupe_phash_enabled`; Vergleich **immer** `distance == 0` — `dupe_threshold` wird ignoriert (reuse via `_compare_chunk(..., threshold=0)`, Hamming-Distanz ist nie negativ)
- [x] CLIP-Pfad:
  - [x] Alle Assets mit `clip_embedding IS NOT NULL` laden (id + blob)
  - [x] Chunked über `_compare_chunk_clip` iterieren (`_COMPARISON_CHUNK_CLIP = 1000`)
  - [x] Gefundene Paare gesammelt (direkt in die Merge-Struktur statt Zwischenliste)
- [x] `found` zusammenführen: DHash-Set ∪ CLIP-Set, Duplikate auflösen
  - Ein Paar kann in beiden Sets stecken → beide Distanzen behalten
  - Datenstruktur: `dict[tuple[int,int], _PairMatch]` (Dataclass statt String-Keyed Dict — mypy-strict-sauber, kein Feld-Typo-Risiko)
- [x] `_insert_pairs` Signatur erweitert: nimmt jetzt `list[tuple[int, int, int | None, float | None]]`
- [x] `ON CONFLICT DO NOTHING` bleibt — bestehende Pairs nicht überschreiben

### Similar-Endpoint update (Lightbox)

- [x] `GET /assets/{id}/similar` in `review.py`:
  - pHash-Suche nur wenn `dupe_phash_enabled` und `asset.phash is not None`; Treffer nur bei `phash_distance == 0`
  - CLIP-Suche nur wenn `dupe_clip_enabled` und `asset.clip_embedding is not None`
  - CLIP-Suche: sqlite-vec ANN Query (`vector_index.search`) mit Limit = 20, dann filtern nach `clip_distance ≤ threshold`
  - Ergebnis: UNION beider Listen, sortiert nach bestem Score (pHash 0–64 auf 0–1 normiert, damit beide Skalen vergleichbar sind)
- [x] `SimilarAssetDto` um `clip_distance: float | None` erweitert; `phash_distance` musste ebenfalls auf `int | None` — sonst crasht die DTO-Konstruktion bei reinen CLIP-Treffern (kein Feld gesetzt)

---

## Report-Back

- `phash.py`/`_compare_chunk` unverändert wiederverwendet: `threshold=0` reicht für "nur exakte Treffer", da Hamming-Distanz nie negativ ist — spart eine Doppel-Implementierung.
- Datenfluss-Struktur bewusst als kleine `@dataclass` (`_PairMatch`/`_SimilarMatch`) statt `dict[str, ...]` gebaut — lief zunächst über String-Keys, aber mypy (Projekt läuft mit `strict = true`) hat die Typvermischung (`int | float | None`) zu Recht angemeckert. Dataclass ist auch einfach lesbarer.
- **Abweichung von der Checkliste:** `SimilarAssetDto.phash_distance` musste von `int` auf `int | None` — sonst wirft die DTO-Konstruktion einen Validierungsfehler, sobald ein Treffer nur über CLIP kommt. Gleiches Problem existierte bereits am bestehenden `DupePairDto.phash_distance` (nicht in der Phase-2-Checkliste, aber durch den geänderten Scan-Job jetzt real erreichbar) — minimal auf `int | None` geweitet, damit `/review/dupes` nicht crasht. Volle Kontrakt-Form (`triggered_by`, `similarity_pct`) bleibt Phase 3, siehe FINDINGS.md.
- Mypy-Strict-Check (`strict = true` in `pyproject.toml`) lief sauber gegen beide Dateien; Projekt-Baseline sogar von 102 auf 100 Fehler gesunken (ein vorbestehender Fehler im alten Scan-Job war Kollateralschaden meiner Umschreibung).
