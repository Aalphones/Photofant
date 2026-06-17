# STATE — Photofant

> Kanonischer Resume-Pointer für laufende Implementierung. Wird bei jeder Phasengrenze aktualisiert, **nie** gelöscht.

## Aktiver Plan

**P5 — Klassifizierung** · [`docs/planning/2026-06-12_p05-klassifizierung/`](docs/planning/2026-06-12_p05-klassifizierung/README.md)

**Phase:** 5/6 — Heuristiken & Pipeline-Integration (pending)

**Nächster Schritt:** Phase 5 starten — `POST /classify/rerun` (Bulk/Single-Neuberechnung mit Ledger-Reset je Step, inkl. neuem `embedding_done`), Heuristiken (`quality_score`, `framing`), `classified`-Flag, Pipeline-Verdrahtung. Bausteine bereit: `enqueue_tagging/caption/embedding`, `vector_index.rebuild_index`. Details: [phase-5-heuristiken-pipeline.md](docs/planning/2026-06-12_p05-klassifizierung/phase-5-heuristiken-pipeline.md), offene Findings in FINDINGS.md.
