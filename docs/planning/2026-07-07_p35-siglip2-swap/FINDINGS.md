# FINDINGS — P35 SigLIP2-Swap

Erkenntnisse während der Umsetzung, getaggt nach Phase. Format:

- [ ] → Phase N: <Erkenntnis / Abweichung / Nachtrag>

- [x] → Phase 1 (erledigt): Plan zählte 3 Embedder-Konsumenten, es sind **5** — `classification/scoring.py`
  und `api/assets.py` kamen dazu. Alle auf `resolve_image_embedder()` umgestellt.
- [ ] → Phase 2: Der Dim-Guard (`warn_on_embedding_dim_mismatch`) warnt nur, crasht nicht. Nach Anheben von
  `vector_index.EMBEDDING_DIM` auf 1024 (Phase 2) muss der Guard grün sein, sobald SigLIP2 aktiv ist —
  vorher (CLIP aktiv + Index 1024) warnt er absichtlich. Beim Testen der Migration einkalkulieren.
- [ ] → Phase 3: SigLIP2-Preprocessing/Text-Kontrakt sind gegen dokumentierte Specs gebaut, **nicht** gegen
  die echten Config-Dateien verifiziert (Modell war in Phase 1 nicht lokal). Vor der Schwellwert-Kalibrierung
  sicherstellen, dass der Download durch ist und die Verifikation (Smoke #2/#3) sitzt — sonst kalibriert man
  auf stumpfen Embeddings.
