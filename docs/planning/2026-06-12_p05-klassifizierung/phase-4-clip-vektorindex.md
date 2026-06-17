# P5 · Phase 4 — CLIP-Embeddings & Vektor-Index

> Rating: **heikel** (Architektur-Entscheidung Vektor-Backend fällt hier → ADR) · Status: pending

## Kontext (vorher lesen)

- [README.md](README.md) — Kontrakt
- [Konzept](../../Konzept-Photofant.md) §3 (sqlite-vec oder FAISS), §10 (semantische Suche), §16 (Vektorsuche)

## Akzeptanzkriterien

- **ADR-001** (`docs/decisions/001-vektor-backend.md`): `sqlite-vec` vs. FAISS — Kriterien: eine Datei vs. Zusatz-Index, Persistenz, Windows-Wheels, Performance bei ~100k Vektoren. Default-Empfehlung `sqlite-vec`; Entscheidung fällt nach kurzem Spike, nicht nach Gefühl.
- CLIP/SigLIP-Image-Embedding pro Asset (Ledger-gesteuert), Ablage in `asset.clip_embedding` + Index; Text-Encoder für Query-Embedding.
- `POST /api/search/semantic` — `{ query: string }` oder `{ like_asset_id: number }` → Top-N Asset-Ids + Scores (Cosine).
- Index übersteht Backend-Neustart (persistent oder beim Start aus der DB rekonstruiert — ADR-Folge).

## Checkliste

- [x] Spike + ADR-001 schreiben → [ADR-001](../../decisions/001-vektor-backend.md): sqlite-vec (Spike auf Windows/CPython 3.12 bestätigt)
- [x] `Embedder`-Implementierung (Image- + Text-Pfad, Normalisierung) → `inference/adapters/clip.py`, CLIP-eigene Normalisierung in `preprocessing.py`
- [x] Index-Aufbau/-Pflege (insert bei Import, delete bei endgültigem Löschen) → `db/vector_index.py`, Import-Job + `moves.purge`
- [x] Semantic-Search-Endpoint → `POST /api/search/semantic` (`api/search.py`)
- [x] Doc-Update: docs/models.md (Embedding-Ablage, vec0-Tabelle), routes.md

## Report-Back

**Status: complete (2026-06-17).**

- **ADR-001 = sqlite-vec**, nicht nach Gefühl: Spike auf der Zielplattform (Windows 10,
  CPython 3.12) bestätigt `enable_load_extension`, das `sqlite-vec`-Wheel lädt, `vec0` mit
  `distance_metric=cosine` liefert korrekte KNN-Ergebnisse. FAISS verworfen (zweiter
  Persistenz-Mechanismus ohne Nutzen in der ~100k-Größenordnung).
- **Index in `db.sqlite`** (`vec_asset_embedding`, rowid = asset.id) — persistent, übersteht
  Neustart ohne Rekonstruktion. Source of Truth bleibt `asset.clip_embedding` (BLOB); der
  Index ist daraus per `rebuild_index()` neu aufbaubar (Drift vorwärts-heilbar).
- **Extension pro Connection** via SQLAlchemy-`connect`-Event (`db/engine.py`) und in
  Migration 0007 (auf `op.get_bind()`).
- **Korrektur:** CLIP nutzt **eigene** Normalisierungs-Stats, nicht ImageNet — `normalize_clip`
  ergänzt, `preprocess_for_clip` umgestellt (vorher fälschlich ImageNet).
- **CLIP-Manifest** auf HF-Snapshot umgestellt (getrennter Vision-/Text-Encoder + Tokenizer
  statt kombiniertem `model.onnx`), analog Florence.
- **Akzeptanzkriterium 5 (API-Test):** Da im private-Profil keine Tests geschrieben werden,
  end-to-end mit synthetischen 768-dim-Embeddings über ein Wegwerf-Skript verifiziert:
  Schema (vec0/embedding_done/FK), korrekte Cosine-Ordnung, Delete, Rebuild — alles grün.
  Echter „red dress"-Smoke-Test braucht heruntergeladene CLIP-Gewichte (User-Smoke-Checkliste).
