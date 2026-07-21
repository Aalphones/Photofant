"""Websuche für die Discovery-Capability (P38) — kein Agenten-Loop, kein Tool-Routing.

Wird direkt vom KnowledgeDiscoveryJob aufgerufen (gleiche Direktaufruf-Konvention wie
KnowledgeService in den bestehenden P27-Jobs). Einziger Netzwerkzugriff der Wissensbasis
mit echtem Internet-Bezug — Opt-in pro Aktion (ADR-031), alle anderen KI-Funktionen
bleiben offline (P27-AK).
"""
from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import Any

log = logging.getLogger(__name__)


@dataclass(frozen=True)
class WebSearchResult:
    title: str
    url: str
    snippet: str


class WebSearchError(RuntimeError):
    """Suche fehlgeschlagen (Netzwerk, Paket fehlt, Rate-Limit) — Job wandelt das in einen
    Job-Fehlerstatus um, kein stiller Fallback wie bei der GGUF-Verfügbarkeitsprüfung."""


def search_web(query: str, max_results: int = 5) -> list[WebSearchResult]:
    """Suche *query* im Web und liefere bis zu *max_results* Treffer.

    Import bewusst lazy: `ddgs` steckt im Extra `web-discovery`; ohne installiertes
    Paket soll der Rest der Anwendung normal starten und erst der Klick auf
    „Recherchieren" eine verständliche Fehlermeldung erzeugen.
    """
    try:
        from ddgs import DDGS
    except ImportError as error:
        raise WebSearchError(
            "Websuche nicht verfügbar — Paket fehlt. "
            "Install: uv pip install 'photofant[web-discovery]'"
        ) from error

    try:
        with DDGS() as client:
            raw_results: list[dict[str, Any]] = list(client.text(query, max_results=max_results))
    except Exception as error:  # Netzwerk-/Rate-Limit-Fehler der Bibliothek, nicht typisiert
        raise WebSearchError(f"Websuche fehlgeschlagen: {error}") from error

    # Verifiziert gegen ddgs 9.14.4: title/href/body. `url`/`snippet` decken die
    # älteren Key-Namen der Bibliothek mit ab (kein SLA auf die Rückgabe-Form).
    results = [
        WebSearchResult(
            title=item.get("title", ""),
            url=item.get("href", "") or item.get("url", ""),
            snippet=item.get("body", "") or item.get("snippet", ""),
        )
        for item in raw_results
        if item.get("href") or item.get("url")
    ]
    log.debug("Websuche %r → %d Treffer", query, len(results))
    return results
