# FINDINGS — MCP-Schnittstelle

> Erkenntnisse während der Umsetzung, die spätere Phasen betreffen. Format:
> `- [ ] → Phase N: <Erkenntnis>` · abgehakt, wenn in der Zielphase berücksichtigt.

- [x] → Phase 2: Tools werden nur registriert, wenn ihr Modul **importiert** wird (der `@mcp_server.tool()`-Decorator läuft beim Import). `ping` steht direkt in `mcp/server.py`. Neue `mcp/tools/*.py` müssen in `server.py` importiert werden (z. B. `from photofant.mcp.tools import library  # noqa: F401`), sonst taucht das Tool im Client nicht auf.
- [x] → Phase 2: Settings gehen über das generische `/api/config` (kein `/api/settings/mcp`). `view_photo` muss `mcp.return_images` (Bild vs. nur Metadaten) und `mcp.thumbnail_size` respektieren; beide liegen fertig im `mcp`-Block. Bild-Content als MCP-`ImageContent`, genau ein Bild pro Aufruf.
- [x] → Phase 2: Listen-Tools auf `mcp.max_search_results` deckeln und `total` mitgeben (Kontrakt README). `run_endpoint(list_assets, ...)` liefert bereits `AssetsPage.total`.
- [ ] → Phase 3/4/5/6: `get_capabilities` (`api/models.py`) ist **synchron** (kein `Awaitable`) — `run_endpoint()` erwartet eine async Coroutine und würde daran scheitern. Falls weitere Endpoints ebenfalls sync sind: direkt mit eigenem `db_session()` aufrufen statt `run_endpoint()`.
- [ ] → Phase 2 (erledigt, für Folge-Tools relevant): Ein Tool, das ein Nicht-Pydantic-Objekt zurückgibt (z. B. `mcp.server.fastmcp.Image` bei `view_photo`), muss mit `@mcp_server.tool(structured_output=False)` registriert werden — sonst crasht die Tool-Registrierung beim Schema-Bau (`PydanticSchemaGenerationError`).
- [ ] → Phase 2 (erledigt, für Folge-Tools relevant): `GET /jobs/{id}` existiert nicht — `get_job_status`/`list_jobs` lesen direkt `job_queue.snapshot()` (Modul-Singleton aus `jobs/queue.py`), kein `run_endpoint()`/keine DB-Session nötig.

