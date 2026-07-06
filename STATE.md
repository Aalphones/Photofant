# STATE

**Aktiver Plan:** `docs/planning/2026-07-03_p33-phash-abloesung/`
**Phase:** 2/4 — Trainingssets + Face-Dedupe Backend (offen)
**Nächster Schritt:** `/clear`, dann `/implement` — Phase 2 ist standard-Komplexität, `sonnet` reicht.

Phase 1 (Dupe-Pipeline Backend) fertig: Post-Embedding-Dupe-Check via sqlite-vec,
Dupe-Scan-Job/`/api/duplicates`/`/api/review` laufen CLIP-only, Rerun-Step „phash" weg.
Abweichung: `dupe_threshold` bleibt in `settings.py` erhalten, bis Phase 2
`api/collections.py` umbaut (sonst Crash dort) — Details in FINDINGS.md des Plans.
Tests: 189 grün, 13 vorbestehende Fails unberührt (per Stash-Vergleich verifiziert).
