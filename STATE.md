# STATE — Photofant

> Kanonischer Resume-Pointer für laufende Implementierung. Wird bei jeder Phasengrenze aktualisiert, **nie** gelöscht.

## Aktiver Plan

**P5 — Klassifizierung** · [`docs/planning/2026-06-12_p05-klassifizierung/`](docs/planning/2026-06-12_p05-klassifizierung/README.md)

**Phase:** 4/6 — CLIP-Embeddings & Vektor-Index (pending)

**Nächster Schritt:** CLIP-ViT-L/14-Embedder implementieren (`photofant/inference/adapters/clip.py`) — `Embedder.embed(image) → ndarray`, 224er Center-Crop-Preprocessing (existiert), Embedding-Job + `sqlite-vec`-Index, „mehr wie dieses"-API-Test.
