# Phase 2 — Backend-Engine (Scan + Similar)

**Tier:** heikel  
**Status:** pending

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

- [ ] `run_dupe_scan_job` nutzt DHash wenn `dupe_phash_enabled`, CLIP wenn `dupe_clip_enabled`
- [ ] Ergebnis ist die Vereinigung (UNION) beider Methoden — kein Paar doppelt
- [ ] Für CLIP-Paare: `phash_distance = NULL`, `clip_distance` gesetzt
- [ ] Für DHash-Paare: `phash_distance` gesetzt, `clip_distance = NULL`
- [ ] Für Paare die von beiden erkannt werden: beide Felder gesetzt
- [ ] CLIP-Scan läuft in 1000er-Blöcken (Outer-Loop), bleibt unter 50 MB RAM-Peak pro Chunk
- [ ] Assets ohne `clip_embedding` werden im CLIP-Scan übersprungen (kein Fehler)
- [ ] `GET /assets/{id}/similar` (Lightbox) gibt CLIP-Treffer zurück wenn `dupe_clip_enabled` — ergänzt DHash-Treffer (UNION, nach Ähnlichkeit sortiert)
- [ ] Beide Methoden deaktiviert → kein Scan / keine Similar-Results (kein Crash)

---

## Checkliste

### CLIP-Pairwise-Vergleich (Hilfsfunktion)

- [ ] Neue Funktion `_compare_chunk_clip` in `dupe_scan_job.py` (analog zu `_compare_chunk`)
  ```python
  def _compare_chunk_clip(
      asset_embeddings: list[tuple[int, bytes]],  # (asset_id, blob)
      start: int,
      end: int,
      threshold: float,                            # Cosine-Distance
  ) -> list[tuple[int, int, float]]:              # (a_id, b_id, clip_distance)
  ```
- [ ] Embeddings deserialisieren: `np.frombuffer(blob, dtype=np.float32)` (768-dim, bereits L2-normiert)
- [ ] Chunk-Matrix `A = stack(embeddings[start:end])` (shape: chunk×768)
- [ ] Rest-Matrix `B = stack(embeddings)` (shape: N×768)
- [ ] `sims = A @ B.T` → Cosine-Similarity (da L2-normiert = Dot-Product)
- [ ] `dists = 1.0 - sims` → Cosine-Distance
- [ ] Pairs wo `dist ≤ threshold` und `i < j` sammeln (kein Selbst-Vergleich, kein Doppel)

### Scan-Job update

- [ ] `run_dupe_scan_job`: Settings-Felder `dupe_phash_enabled`, `dupe_clip_enabled`, `dupe_clip_threshold` laden
- [ ] DHash-Pfad nur ausführen wenn `dupe_phash_enabled`
- [ ] CLIP-Pfad:
  - [ ] Alle Assets mit `clip_embedding IS NOT NULL` laden (id + blob)
  - [ ] Chunked über `_compare_chunk_clip` iterieren (COMPARISON_CHUNK = 1000)
  - [ ] Gefundene Paare in `clip_pairs: list[tuple[int, int, float]]` sammeln
- [ ] `found_pairs` zusammenführen: DHash-Set ∪ CLIP-Set, Duplikate auflösen
  - Ein Paar kann in beiden Sets stecken → beide Distanzen behalten
  - Datenstruktur: `dict[tuple[int,int], dict]` mit `phash_distance` und `clip_distance` je Optional
- [ ] `_insert_pairs` Signatur erweitern: nimmt jetzt `list[tuple[int, int, int | None, float | None]]`
- [ ] `ON CONFLICT DO NOTHING` bleibt — bestehende Pairs nicht überschreiben
  🟡 Bei erneutem Scan eines Paars, das vorher nur DHash hatte, würde `clip_distance` nicht nachgetragen — das ist akzeptabel; ein Vollscan schreibt nur neue Paare

### Similar-Endpoint update (Lightbox)

- [ ] `GET /assets/{id}/similar` in `review.py`:
  - DHash-Suche nur wenn `dupe_phash_enabled` und `asset.phash is not None`
  - CLIP-Suche nur wenn `dupe_clip_enabled` und `asset.clip_embedding is not None`
  - CLIP-Suche: sqlite-vec ANN Query (`vector_index.search`) mit Limit = 20, dann filtern nach `clip_distance ≤ threshold`
  - Ergebnis: UNION beider Listen, nach bestem Ähnlichkeits-Score sortiert (kleinste Distance first)
- [ ] `SimilarAssetDto` um `clip_distance: float | None` erweitern (phash_distance bleibt)

---

## Report-Back

_Hier trägt der Umsetzer nach Abschluss ein was abwich oder auffiel._
