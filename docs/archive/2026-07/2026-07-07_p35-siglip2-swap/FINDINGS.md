# FINDINGS — P35 SigLIP2-Swap

Erkenntnisse während der Umsetzung, getaggt nach Phase. Format:

- [ ] → Phase N: <Erkenntnis / Abweichung / Nachtrag>

- [x] → Phase 1 (erledigt): Plan zählte 3 Embedder-Konsumenten, es sind **5** — `classification/scoring.py`
  und `api/assets.py` kamen dazu. Alle auf `resolve_image_embedder()` umgestellt.
- [x] → Phase 2 (erledigt): Der Dim-Guard (`warn_on_embedding_dim_mismatch`) warnt nur, crasht nicht.
  `EMBEDDING_DIM` steht jetzt auf 1024; der Guard liest die Konstante live (keine Code-Änderung nötig).
  Erwartetes Verhalten nach der Migration: mit CLIP aktiv (768) warnt er absichtlich, mit SigLIP2 aktiv (1024)
  ist er grün. → Beim User-Smoke einkalkulieren: der Warn-Log beim Start ist bis zum SigLIP2-Aktivieren normal.
- [x] → Phase 3 (erledigt): SigLIP2-Text-Preprocessing gegen die echte `tokenizer.json` verifiziert —
  Padding-Strategie (Fixed:64, pad_id=0, pad_token=`<pad>`) ist im Export bereits korrekt gebacken, unser
  Adapter-Code (`enable_truncation(64)` + `enable_padding(64)`) deckt sich damit. Kein Bug hier.
- [x] → Phase 3 (erledigt, kritisch): Exklusivitäts-Invariante („genau ein Bild-Embedder aktiv") wurde zur
  Laufzeit verletzt (CLIP + SigLIP2 beide `enabled=1`) und hat die Textsuche mit einem Dimension-Mismatch
  zum Absturz gebracht. Resolver ist jetzt selbstheilend — Details: Phase-3-Datei, Deviation 4, ADR-021.
