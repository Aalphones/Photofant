# STATE

**Aktiver Plan:** `docs/planning/2026-07-03_p33-phash-abloesung/`
**Phase:** 3/4 — Frontend-Anpassung (offen)
**Nächster Schritt:** `/clear`, dann `/implement` — Phase 3 ist mechanisch, `sonnet` reicht.

Phase 2 (Trainingssets + Face-Dedupe Backend) fertig: `/collections/{id}/duplicates`
und `compute_training_set_stats` laufen CLIP-only (`clip_distance`/`similarity_pct`),
Face-Dedupe bei Edit-Versionen vergleicht buffalo_l-Embeddings statt pHash. Kein Code
schreibt mehr `Asset.phash`/`Face.phash` (Spalten fallen in Phase 4). `dupe_threshold`
final aus `settings.py`/`settings.example.json` entfernt; neu: `training_near_dupe_clip_threshold`
(0.05), `face_dedupe_similarity_threshold` (0.9). Frontend (`models.effects.ts` liest noch
`dupe_threshold`) ist bewusst unangetastet — das ist Phase 3.
Tests: 189 grün, 13 vorbestehende Fails unberührt (identisch zu Phase 1).
