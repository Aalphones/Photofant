# FINDINGS — MCP-Schnittstelle

> Erkenntnisse während der Umsetzung, die spätere Phasen betreffen. Format:
> `- [ ] → Phase N: <Erkenntnis>` · abgehakt, wenn in der Zielphase berücksichtigt.

- [ ] → Phase 2: Tools werden nur registriert, wenn ihr Modul **importiert** wird (der `@mcp_server.tool()`-Decorator läuft beim Import). `ping` steht direkt in `mcp/server.py`. Neue `mcp/tools/*.py` müssen in `server.py` importiert werden (z. B. `from photofant.mcp.tools import library  # noqa: F401`), sonst taucht das Tool im Client nicht auf.
- [ ] → Phase 2: Settings gehen über das generische `/api/config` (kein `/api/settings/mcp`). `view_photo` muss `mcp.return_images` (Bild vs. nur Metadaten) und `mcp.thumbnail_size` respektieren; beide liegen fertig im `mcp`-Block. Bild-Content als MCP-`ImageContent`, genau ein Bild pro Aufruf.
- [ ] → Phase 2: Listen-Tools auf `mcp.max_search_results` deckeln und `total` mitgeben (Kontrakt README). `run_endpoint(list_assets, ...)` liefert bereits `AssetsPage.total`.

