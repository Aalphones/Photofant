# STATE

**Aktiver Plan:** `docs/planning/2026-07-06_mcp-schnittstelle/`
**Phase:** 5/6 — Import, Organisieren, Duplikate — pending
**Nächster Schritt:** Phase 5 umsetzen nach `phase-5-import-organisieren-duplikate.md` (Kontext-Diät:
README + eigene Phasen-Datei + FINDINGS.md-Einträge für Phase 5 lesen, nicht mehr). Modell: `sonnet`
reicht (Komplexität standard).

**Backlog danach (User-Reihenfolge, 2026-07-07):** MCP-Plan fertig (Phase 5+6, archivieren) →
`2026-07-07_p35-siglip2-swap` → `2026-07-07_p36-reverse-image-search` →
`2026-07-07_p37-dinov2-reranking` → `2026-07-01_p22-knowledge-engine` bis `p26-recommendation-engine`
(in Nummernreihenfolge) → `2026-07-06_p34-mcp-wissensbasis` → `2026-07-01_p27-gemma-integration`.

_Phase 4 fertig (13 Write-Tools in `mcp/tools/persons.py`: create/rename/assign/bulk_assign/merge/
split/delete_person, list_faces/get_face_matches/delete_face, recluster, list_face_review/
resolve_face_review — Gate auf merge_persons/delete_person/delete_face), ruff/mypy grün, alle 33
Tools registrieren fehlerfrei (`mcp_server.list_tools()` geprüft). Kein Live-Smoke in dieser Phase
(private-Profil: Smoke einmal am Plan-Ende, durch den User) — offen bleibt weiterhin der
Live-MCP-Handshake gegen `/mcp` (seit Phase 1, oberste Wackelstelle, noch nicht ausgeführt)._
