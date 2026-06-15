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

- [ ] Spike + ADR-001 schreiben
- [ ] `Embedder`-Implementierung (Image- + Text-Pfad, Normalisierung)
- [ ] Index-Aufbau/-Pflege (insert bei Import, delete bei endgültigem Löschen)
- [ ] Semantic-Search-Endpoint
- [ ] Doc-Update: docs/models.md (Embedding-Ablage), routes.md

## Report-Back
