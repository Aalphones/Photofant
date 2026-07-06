# STATE

**Aktiver Plan:** `docs/planning/2026-07-03_p33-phash-abloesung/`
**Phase:** 4/4 — Ausbau: DB-Migration, Modul-Löschung, Docs, ADR-018 (offen)
**Nächster Schritt:** `/clear`, dann `/implement` — Phase 4 ist mechanisch, `sonnet` reicht.

Phase 3 (Frontend-Anpassung) fertig: kein `phash`/`triggeredBy` mehr unter `frontend/src/`
(Modelle, Services, Store, Review-Dupes-UI, Personen-Dupe-Check, Rerun-Dialog, Einstellungen,
Trainingsset-Dupes-Slider auf %-Basis, Lightbox). `npm run lint && npm run build` grün.

Dabei Backend-Nebenfund behoben (siehe FINDINGS.md → Phase 4, bereits erledigt markiert):
`AssetDto.has_phash` (`api/assets.py`) war seit Phase 1 für jedes neu importierte Bild
`false` — der „Ähnliche Bilder"-Button im Lightbox war seither für neue Assets unbemerkt
deaktiviert. Umbenannt auf `has_embedding` (`asset.clip_embedding is not None`), inkl.
Batch-Query in `list_assets` gegen N+1 auf der deferred BLOB-Spalte. `test_assets_search.py`
(6 Tests) grün.

Phase 4 muss dieses Feld **nicht** mehr anfassen — der Grep-Sweep zeigt hier bereits 0 Treffer.
