# STATE

**Aktiver Plan:** `docs/planning/2026-07-06_mcp-schnittstelle/`
**Phase:** 2/6 — Finden & Ansehen (Read-Tools inkl. Bild-Content, Job-Status) — pending
**Nächster Schritt:** Phase 2 umsetzen: `mcp/tools/library.py` (search/get/view_photo/facets/similar/lineage/capabilities/jobs), Modul in `server.py` importieren (FINDINGS Phase-2-Notiz). Deckel `mcp.max_search_results`, Bilder als `ImageContent` per `mcp.return_images`/`thumbnail_size`.

_Phase 1 fertig (Backend-MCP-Kern + Settings + Frontend-Sektion + ADR-019 + Docs), ruff/mypy/ng build grün. Offen: User-Smoke des Live-Handshakes gegen `/mcp` (oberste Wackelstelle)._
