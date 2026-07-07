"""MCP-Tool-Module — je Phase ein Modul (library, metadata, persons, organize, maintenance).

Jedes Modul registriert seine Tools per `@mcp_server.tool()`-Decorator als Import-Nebeneffekt
(siehe FINDINGS.md Phase 2) — es muss dafür in `server.py` importiert werden.
"""
from __future__ import annotations
