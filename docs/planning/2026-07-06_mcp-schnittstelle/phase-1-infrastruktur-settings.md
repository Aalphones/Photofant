# Phase 1 — MCP-Infrastruktur + Settings-Toggle + Warnhinweis-UI

**Komplexität:** heikel (neue Library, ASGI-Mount + Lifespan, Security, Laufzeit-Toggle) · **Status:** pending

## Kontext (vor dem Bauen lesen)

- `README.md` dieses Plans — Kontrakt, Leitplanken, Konfidenz-Ausweis.
- `backend/photofant/main.py` — `create_app()`, `include_router`-Muster, `_lifespan`-Contextmanager.
- `backend/photofant/settings.py` — `AppSettings`-TypedDict, `SETTINGS_DEFAULTS`, `_EXPECTED_TYPES`,
  der `comfyui`-Nested-Block als **Vorlage** für den neuen `mcp`-Block, `patch_settings()`-Validierung.
- `backend/photofant/api/assets.py` — wie ein Endpoint die DB-Session via `Depends` bezieht (Vorlage
  für `adapter.py:run_endpoint()`) und wie `list_assets` signiert ist (Adapter-Testziel).
- `frontend/src/app/features/einstellungen/comfyui/` — Vorlage für die neue MCP-Settings-Sektion
  (Toggle + Felder + Speichern über `SettingsService`).
- `frontend/src/app/models/config.model.ts` — `AppSettings`-Frontend-Typ, hier `mcp`-Block ergänzen.
- MCP Python SDK: offizielles Paket `mcp` (`from mcp.server.fastmcp import FastMCP`), Streamable-HTTP-App
  via `mcp.streamable_http_app()`. Dependency neu aufnehmen (→ `mode-dependencies`).

## AK (falsifizierbar)

- [ ] `pyproject.toml` enthält `mcp>=1.2` (oder aktuelle stabile Minor); `uv lock` läuft durch.
- [ ] Neuer `mcp`-Block in `settings.py`: `AppSettings`-TypedDict, `SETTINGS_DEFAULTS`, `_EXPECTED_TYPES`
      (`"mcp": dict`) — Keys/Defaults exakt wie in der README-Sektion „settings.json".
- [ ] `backend/photofant/mcp/server.py`: FastMCP-Instanz `mcp_server`, Mount-Helper
      `mount_mcp(app: FastAPI)`, aufgerufen am Ende von `create_app()`.
- [ ] `/mcp` ist gemountet, aber eine **Flag-Guard-Middleware** liest bei jedem Request `mcp.enabled`
      live aus `load_settings()` und antwortet `404`, wenn aus — **ohne** Prozess-Neustart umschaltbar.
- [ ] Der MCP-Server bindet nur über den bestehenden Uvicorn-Loopback; eine `Host`/`Origin`-Prüfung
      lehnt Nicht-Loopback-Header mit `403` ab (DNS-Rebinding-Schutz).
- [ ] Der FastAPI-`_lifespan` startet/stoppt den MCP-Session-Manager sauber mit (kombinierter Lifespan);
      Backend startet ohne Fehler mit `mcp.enabled` an **und** aus.
- [ ] `backend/photofant/mcp/adapter.py:run_endpoint()` öffnet eine DB-Session (Muster aus `api/assets.py`)
      und ruft eine Endpoint-Coroutine damit auf. Bewiesen an einem Smoke-Tool `ping` (gibt Bildzahl +
      DB-Pfad zurück, ruft intern `list_assets`/`info`).
- [ ] `backend/photofant/mcp/gate.py:confirmation_required(action_desc, confirm)` — gibt bei
      `confirm=false` eine Klartext-Warnung zurück (noch von keinem Tool genutzt, nur bereitgestellt).
- [ ] Frontend: neue Einstellungen-Sektion „MCP-Schnittstelle" (Route/Nav analog `comfyui/`), mit:
  - [ ] Toggle `mcp.enabled` (Default aus), Toggle `mcp.return_images`, Zahlenfelder
        `max_search_results` / `thumbnail_size`, Toggle `mcp.require_confirm`.
  - [ ] **Unübersehbares Warn-Banner** (Warn-Farbe, Icon): „Nur mit lokal laufenden Agenten nutzen —
        sonst landen deine Bilder und Metadaten beim Cloud-Anbieter."
  - [ ] Kopierbare Verbindungs-URL `http://127.0.0.1:<backend-port>/mcp` + ein Satz „So verbindest du
        einen lokalen Agenten".
  - [ ] **Kopierbarer JSON-Codeblock** mit der fertigen MCP-Client-Konfiguration zum Einrichten (Muster
        `mcpServers`-Eintrag), mit der **echten** Base-URL der laufenden App gefüllt (nicht Platzhalter —
        das Frontend kennt seine API-Base-URL über die `environment`-Config). Copy-Button. Beispiel:
        ```json
        {
          "mcpServers": {
            "photofant": {
              "url": "http://127.0.0.1:8000/mcp"
            }
          }
        }
        ```
        Da der Transport Streamable-HTTP ist (ADR-019), ist die `url`-Variante oben der **Default**.
        Darunter, dezent als „Alternative für stdio-only Clients" (z. B. ältere Claude-Desktop-Stände),
        die Bridge-Variante:
        ```json
        {
          "mcpServers": {
            "photofant": {
              "command": "npx",
              "args": ["mcp-remote", "http://127.0.0.1:8000/mcp"]
            }
          }
        }
        ```
  - [ ] Je Einstellung ein dezentes `i`/`?`-Tooltip (Idiotensicherheits-Gate: jede Option erklärt).
- [ ] ADR-019 `docs/decisions/019-mcp-schnittstelle.md` angelegt (Kontext / Optionen: eingebettet vs.
      eigener stdio-Prozess, offizielles SDK vs. fastmcp v2, Auth-frei / Optionen / Konsequenzen).

## Umsetzung — Checkliste

- [ ] Dependency `mcp` aufnehmen, `uv lock`, Import-Smoke.
- [ ] `mcp`-Settings-Block (Backend + Frontend-Typ) nach README-Spec.
- [ ] `mcp/server.py`: FastMCP-Instanz, `streamable_http_app()`-Mount, Lifespan-Verkettung in `main.py`.
- [ ] Flag-Guard- + Host-Check-Middleware vor dem Mount.
- [ ] `mcp/adapter.py:run_endpoint()` + Smoke-Tool `ping`.
- [ ] `mcp/gate.py:confirmation_required()`.
- [ ] Frontend-Sektion inkl. Warn-Banner, URL-Copy, Tooltips.
- [ ] ADR-019 schreiben.
- [ ] Doc: `docs/code-map.md` (neue Zeile `mcp/`), `docs/routes.md` (neuer MCP-Abschnitt, Grundgerüst),
      `AGENTS.md` (ADR-Liste um 019 ergänzen).

## Report-Back
