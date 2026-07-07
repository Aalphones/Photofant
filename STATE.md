# STATE

**Aktiver Plan:** `docs/planning/2026-07-06_mcp-schnittstelle/`
**Phase:** 4/6 — Personen & Faces — pending
**Nächster Schritt:** Phase 4 umsetzen nach `phase-4-personen-faces.md` (Kontext-Diät: README + eigene
Phasen-Datei + FINDINGS.md-Einträge für Phase 4 lesen, nicht mehr).

_Phase 3 fertig (9 Write-Tools in `mcp/tools/metadata.py`: edit_tags, bulk_edit_tags, set_caption,
set_photo_meta, set_classification, list_tags, rename_tag, merge_tags, set_tag_aliases), ruff/mypy
grün. Zwei kleine Deviations vom Plan-Wortlaut dokumentiert (siehe Phase-3-Datei: `set_classification`
nutzt `steps` statt eines nicht existierenden `labels`-Parameters; `list_tags` ergänzt `total` per
Zusatz-Query). Kein Live-Smoke in dieser Phase (private-Profil: Smoke einmal am Plan-Ende, durch den
User) — offen bleibt weiterhin der Live-MCP-Handshake gegen `/mcp` (seit Phase 1, oberste Wackelstelle,
noch nicht ausgeführt)._
