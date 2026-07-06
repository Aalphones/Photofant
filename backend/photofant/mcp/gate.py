"""Confirmation-Gate für destruktive MCP-Tools.

Reversible Aktionen (Papierkorb, Favorit, Personen-Zuordnung) laufen ohne Gate.
Harte, nicht-reversible Aktionen (endgültig löschen, mergen, Reparatur) rufen
:func:`confirmation_required` auf: ohne ``confirm=true`` führen sie nichts aus,
sondern geben die zurückgegebene Klartext-Warnung an den Agenten zurück.

Global abschaltbar per ``mcp.require_confirm`` (Default true).
"""
from __future__ import annotations

from photofant.settings import load_settings


def confirmation_required(action_desc: str, confirm: bool) -> str | None:
    """Prüft, ob ein destruktives Tool ausgeführt werden darf.

    Rückgabe:
      - ``None`` → grün, das Tool darf fortfahren (``confirm=true`` gesetzt, oder
        das Gate ist global via ``mcp.require_confirm=false`` abgeschaltet).
      - ``str`` → eine an den Agenten zurückzugebende Klartext-Warnung; das Tool
        darf **nichts** ausführen.
    """
    require_confirm = load_settings().get("mcp", {}).get("require_confirm", True)
    if not require_confirm or confirm:
        return None
    return (
        f"Bestätigung nötig — {action_desc}. "
        "Diese Aktion ist nicht umkehrbar und wurde NICHT ausgeführt. "
        "Rufe dasselbe Tool erneut mit confirm=true auf, um sie wirklich durchzuführen."
    )
