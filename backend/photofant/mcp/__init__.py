"""MCP-Schnittstelle — Photofant per lokalem Agenten verwalten (ADR-019).

Eingebettet ins FastAPI-Backend als ASGI-Mount unter ``/mcp``. Auth-frei,
Loopback-only, per Settings-Flag gegated (Default aus). Tools rufen die
vorhandenen ``api/*.py``-Endpoint-Funktionen über :mod:`photofant.mcp.adapter`
direkt auf — keine Doppel-Logik, kein interner HTTP-Loopback.
"""
