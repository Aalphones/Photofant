# FINDINGS — P35 SigLIP2-Swap

Erkenntnisse während der Umsetzung, getaggt nach Phase. Format:

- [ ] → Phase N: <Erkenntnis / Abweichung / Nachtrag>

- [x] → Phase 1 (erledigt): Plan zählte 3 Embedder-Konsumenten, es sind **5** — `classification/scoring.py`
  und `api/assets.py` kamen dazu. Alle auf `resolve_image_embedder()` umgestellt.
- [x] → Phase 2 (erledigt): Der Dim-Guard (`warn_on_embedding_dim_mismatch`) warnt nur, crasht nicht.
  `EMBEDDING_DIM` steht jetzt auf 1024; der Guard liest die Konstante live (keine Code-Änderung nötig).
  Erwartetes Verhalten nach der Migration: mit CLIP aktiv (768) warnt er absichtlich, mit SigLIP2 aktiv (1024)
  ist er grün. → Beim User-Smoke einkalkulieren: der Warn-Log beim Start ist bis zum SigLIP2-Aktivieren normal.
- [ ] → Phase 3: SigLIP2-Preprocessing/Text-Kontrakt sind gegen dokumentierte Specs gebaut, **nicht** gegen
  die echten Config-Dateien verifiziert (Modell war in Phase 1 nicht lokal). Vor der Schwellwert-Kalibrierung
  sicherstellen, dass der Download durch ist und die Verifikation (Smoke #2/#3) sitzt — sonst kalibriert man
  auf stumpfen Embeddings.
