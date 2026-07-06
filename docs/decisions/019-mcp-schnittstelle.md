# ADR-019 — MCP-Schnittstelle: eingebettet, auth-frei, Loopback-only

**Status:** Angenommen
**Datum:** 2026-07-06
**Betrifft:** Plan `2026-07-06_mcp-schnittstelle`

---

## Kontext

Photofant soll von einem lokalen KI-Agenten (Claude Desktop, ein lokaler LLM-Client)
gesteuert werden können — praktisch alles, was die UI kann (suchen, ansehen, taggen,
Personen zuordnen, organisieren, Wartung), außer Editor/Generativ. Das Model-Context-
Protocol (MCP) ist der etablierte Standard für solche Agent-Tool-Schnittstellen. Zu
klären war: (1) wie der Server läuft (eigener Prozess vs. eingebettet), (2) welches SDK,
(3) welches Sicherheitsmodell.

## Optionen

**Prozess-Topologie:**
- *Eigener stdio-Prozess* — separater Python-Prozess, der über stdio mit dem Client spricht.
  Verworfen: bräuchte eine zweite Kopie der DB-/Job-/Modell-Logik oder einen HTTP-Rückkanal
  ins Backend. Doppel-Logik, mehr Betriebsteile.
- *Eingebettet ins FastAPI-Backend (gewählt)* — MCP als ASGI-Mount unter `/mcp` im
  bestehenden Prozess. Tools rufen die vorhandenen `api/*.py`-Endpoint-Funktionen direkt als
  async-Funktionen auf (geteilte DB-Session-Factory, geteilte Jobs/Modelle). Keine Doppel-Logik.

**SDK:**
- *Offizielles `mcp`-SDK mit `FastMCP` + Streamable-HTTP (gewählt)* — Referenz-Implementierung,
  ASGI-kompatibel, mountbar. Transport Streamable-HTTP (nicht stdio), damit der Mount in denselben
  Uvicorn läuft.
- *fastmcp v2 (Drittanbieter)* — verworfen, keine Mehrwert-Features für diesen Fall, zusätzliche
  Abhängigkeit außerhalb des offiziellen Stacks.

**Sicherheit (bewusste User-Entscheidung):**
- *Auth/Token/Zertifikat* — verworfen: maximale Reibung für einen reinen Localhost-Anwendungsfall.
- *Auth-frei, aber eingezäunt (gewählt)* — kein Passwort, keine Tokens. Der Schutz ist dreifach:
  (a) Settings-Flag `mcp.enabled`, **Default aus**; (b) Bind nur auf den bestehenden
  Uvicorn-Loopback (`127.0.0.1`); (c) `Host`/`Origin`-Header-Prüfung gegen Loopback (Schutz gegen
  DNS-Rebinding über eine bösartige Webseite).

## Entscheidung

Eingebettete MCP-Schnittstelle unter `/mcp`, offizielles `mcp`-SDK (FastMCP, Streamable-HTTP),
auth-frei / Loopback-only / Flag-gegated.

- **Mount:** `mount_mcp()` am Ende von `create_app()` mountet `mcp_server.streamable_http_app()`
  unter `/mcp`. Der Streamable-HTTP-Session-Manager wird im FastAPI-`_lifespan` mitgestartet
  (`mcp_server.session_manager.run()`) — ein Sub-App-Lifespan wird sonst nie ausgeführt.
- **Laufzeit-Toggle ohne Neustart:** Der Mount existiert immer; eine **Flag-Guard-Middleware**
  (pure ASGI, kein `BaseHTTPMiddleware` — das würde den Stream brechen) liest bei jedem
  `/mcp`-Request live `mcp.enabled` und antwortet 404, wenn aus. So schaltet der Settings-Toggle
  sofort scharf.
- **Tool → Endpoint:** `mcp/adapter.py:run_endpoint()` öffnet eine DB-Session über dieselbe
  Session-Factory wie `Depends(get_session)` und ruft die Endpoint-Coroutine damit auf — jede
  Validierung/Logik bleibt an genau einer Stelle.
- **Confirmation-Gate:** `mcp/gate.py:confirmation_required()` — destruktive Tools verlangen
  `confirm=true`, sonst geben sie nur eine Klartext-Warnung zurück. Reversible Aktionen (Papierkorb,
  Favorit, Personen-Zuordnung) laufen ohne Gate. Global abschaltbar per `mcp.require_confirm`.
- **Bild-Rückgabe:** Bilder ausschließlich über `view_photo` als MCP-`ImageContent`, ein Bild pro
  Aufruf, Größe per `mcp.thumbnail_size` gedeckelt (Token-Budget-Schutz). Abschaltbar per
  `mcp.return_images`.
- **Settings-Block** `mcp` in `settings.json`: `enabled` (default false), `return_images` (true),
  `max_search_results` (50), `thumbnail_size` (256), `require_confirm` (true). Gelesen/geschrieben
  über den generischen `/api/config`-Endpunkt — keine eigene Backend-Route.

## Konsequenzen

- Solange `mcp.enabled` an ist, darf **jeder lokale Prozess** ohne Authentifizierung zugreifen.
  Bewusst akzeptiert für den Localhost-Anwendungsfall; Default aus, unübersehbares Warn-Banner in
  den Einstellungen („Nur mit lokal laufenden Agenten nutzen — sonst landen deine Bilder und
  Metadaten beim Cloud-Anbieter").
- Editor/Generativ und Config-Schreiben bleiben in v1 draußen (Scope-Grenze).
- Neue Abhängigkeit `mcp>=1.2` (aufgelöst auf 1.28.1), zieht u. a. `pydantic-settings`, `httpx-sse`,
  `jsonschema` nach.
- Async-Jobs (Import/Scan/Rerun/Rebuild/Export/Dupe-Scan) geben eine `job_id` zurück; der Agent
  pollt `get_job_status`/`list_jobs` statt auf den SSE-Stream zu warten.
