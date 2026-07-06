"""FastMCP-Instanz, ASGI-Mount und Sicherheits-Middleware der MCP-Schnittstelle.

Der Server wird als Sub-App unter ``/mcp`` in die bestehende FastAPI-App gemountet
(:func:`mount_mcp`, aufgerufen am Ende von ``main.create_app``). Der Session-Manager
des Streamable-HTTP-Transports wird im FastAPI-Lifespan mitgestartet (siehe
``main._lifespan`` → ``mcp_server.session_manager.run()``).

Sicherheit ohne Auth (ADR-019):
  - :class:`McpGuardMiddleware` liest bei **jedem** ``/mcp``-Request live das
    ``mcp.enabled``-Flag aus ``load_settings()`` → 404, wenn aus. So schaltet der
    Settings-Toggle ohne Backend-Neustart scharf.
  - Dieselbe Middleware lehnt Nicht-Loopback ``Host``/``Origin``-Header mit 403 ab
    (Schutz gegen DNS-Rebinding über eine bösartige Webseite).
"""
from __future__ import annotations

import logging

from fastapi import FastAPI
from mcp.server.fastmcp import FastMCP
from starlette.types import ASGIApp, Receive, Scope, Send

from photofant.api.assets import list_assets
from photofant.db.engine import engine
from photofant.mcp.adapter import run_endpoint
from photofant.settings import load_settings

log = logging.getLogger(__name__)

# streamable_http_path="/" → beim Mount unter "/mcp" ergibt sich sauber der
# externe Pfad "/mcp" (statt "/mcp/mcp" beim Default-Pfad "/mcp").
mcp_server = FastMCP("Photofant", streamable_http_path="/")


@mcp_server.tool()
async def ping() -> dict[str, object]:
    """Erreichbarkeits-Check der Photofant-MCP-Schnittstelle.

    Gibt die Zahl der aktiven Bilder und den Datenbank-Pfad zurück — beweist, dass
    der Tool→Endpoint-Adapter mit einer selbst geöffneten DB-Session dieselbe
    Antwort liefert wie der HTTP-Endpoint.
    """
    page = await run_endpoint(list_assets, page=1, page_size=1)
    return {
        "ok": True,
        "asset_count": page.total,
        "database": str(engine.url),
    }


def _hostname(header_value: str) -> str:
    """Extrahiert den Hostnamen aus einem ``Host``/``Origin``-Header (ohne Port/Schema)."""
    value = header_value.strip()
    if "://" in value:
        value = value.split("://", 1)[1]
    # IPv6 in Klammern: [::1]:8000 → ::1
    if value.startswith("["):
        return value[1:].split("]", 1)[0]
    return value.rsplit(":", 1)[0] if ":" in value else value


def _is_loopback(header_value: str) -> bool:
    host = _hostname(header_value)
    return host in {"localhost", "127.0.0.1", "::1"} or host.startswith("127.")


class McpGuardMiddleware:
    """Pure-ASGI-Middleware vor dem gesamten App-Stack.

    Bewusst kein ``BaseHTTPMiddleware`` — das würde die gestreamten Antworten des
    MCP-Transports puffern/brechen. Diese Variante greift nur bei ``/mcp``-Pfaden
    ein und reicht alles andere unverändert durch.
    """

    def __init__(self, app: ASGIApp) -> None:
        self.app = app

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        if scope["type"] != "http" or not scope["path"].startswith("/mcp"):
            await self.app(scope, receive, send)
            return

        settings = load_settings()
        if not settings.get("mcp", {}).get("enabled", False):
            await _reject(send, 404, "Not Found")
            return

        headers = {key.decode("latin-1").lower(): value.decode("latin-1") for key, value in scope["headers"]}
        host = headers.get("host", "")
        origin = headers.get("origin", "")
        if host and not _is_loopback(host):
            await _reject(send, 403, "Forbidden: non-loopback Host header")
            return
        if origin and not _is_loopback(origin):
            await _reject(send, 403, "Forbidden: non-loopback Origin header")
            return

        await self.app(scope, receive, send)


async def _reject(send: Send, status: int, message: str) -> None:
    body = message.encode("utf-8")
    await send({
        "type": "http.response.start",
        "status": status,
        "headers": [(b"content-type", b"text/plain; charset=utf-8")],
    })
    await send({"type": "http.response.body", "body": body})


def mount_mcp(app: FastAPI) -> None:
    """Mountet die MCP-Streamable-HTTP-App unter ``/mcp`` und legt den Sicherheits-Guard davor.

    Am Ende von ``create_app()`` aufrufen. Der Mount existiert immer; ob unter
    ``/mcp`` etwas erreichbar ist, entscheidet live die Guard-Middleware.
    """
    app.mount("/mcp", mcp_server.streamable_http_app())
    app.add_middleware(McpGuardMiddleware)
    log.info("MCP-Schnittstelle unter /mcp gemountet (Zugriff live per mcp.enabled gegated)")
