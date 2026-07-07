# STATE

**Aktiver Plan:** `docs/planning/2026-07-06_mcp-schnittstelle/`
**Phase:** 6/6 — Wartung + Confirmation-Gate scharfstellen — pending
**Nächster Schritt:** Phase 6 umsetzen nach `phase-6-wartung-confirmation-gate.md` (Kontext-Diät:
README + eigene Phasen-Datei + FINDINGS.md-Einträge für Phase 6 lesen, nicht mehr) —
Datei heißt `phase-6-wartung.md`. Modell: `sonnet` reicht (Komplexität standard). Letzte Phase
des Plans — danach Smoke-Checkliste an den User, Doc-Abgleich, Archivieren.

**Backlog danach (User-Reihenfolge, 2026-07-07):** MCP-Plan fertig (Phase 6, archivieren) →
`2026-07-07_p35-siglip2-swap` → `2026-07-07_p36-reverse-image-search` →
`2026-07-07_p37-dinov2-reranking` → `2026-07-01_p22-knowledge-engine` bis `p26-recommendation-engine`
(in Nummernreihenfolge) → `2026-07-06_p34-mcp-wissensbasis` → `2026-07-01_p27-gemma-integration`.

_Phase 5 fertig (23 Write-Tools in `mcp/tools/organize.py`: Import/Scan/Processing,
Papierkorb/Favoriten (Gate auf `empty_trash`), Alben/Trainingssets (Gate auf `delete_collection`),
Duplikate (bedingtes Gate auf `resolve_duplicate` nur bei `delete_a`/`delete_b`). `run_processing`
und `scan_duplicates` rufen ihren Endpoint direkt auf (keine DB-Session nötig, `run_endpoint()`
würde scheitern). `docs/routes.md` MCP-Tabelle ergänzt. ruff/mypy grün, alle 56 Tools registrieren
fehlerfrei. Kein Live-Smoke in dieser Phase (private-Profil: Smoke einmal am Plan-Ende, durch den
User) — offen bleibt weiterhin der Live-MCP-Handshake gegen `/mcp` (seit Phase 1, oberste
Wackelstelle, noch nicht ausgeführt)._
