# STATE

**Aktiver Plan:** `docs/planning/2026-07-06_mcp-schnittstelle/`
**Phase:** 3/6 — Metadaten & Tag-Vokabular (Write, non-destruktiv) — pending
**Nächster Schritt:** Phase 3 umsetzen: `mcp/tools/metadata.py` (edit_tags, bulk_edit_tags, edit_caption, patch_asset, tags/rename/merge/aliases, classify-rerun) nach `phase-3-metadaten-tags.md`, Modul in `server.py` importieren.

_Phase 2 fertig (10 Read-Tools: search/get/view_photo/facets/similar/lineage/capabilities/persons/jobs),
ruff/mypy grün, Smoke gegen echte lokale DB durchlaufen. Offen: User-Smoke des Live-MCP-Handshakes
gegen `/mcp` (seit Phase 1 offen, oberste Wackelstelle — noch nicht ausgeführt)._
