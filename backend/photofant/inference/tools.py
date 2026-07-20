"""Tool registry — the fenced set of actions a capability may take (ADR-027).

Gemma (and later an external MCP agent, P34) never touches the vault directly.
It works through these tools, and **all persistence goes through `KnowledgeService`**
(ownership + validator + Markdown-first). A capability is granted only the tools
it needs: the closed-world `INTERVIEW` gets no search/read tool (private persons
must not be cross-referenced, ADR-009), the import/update capabilities get the
full read + validate + patch set.

Security rule (P27, non-negotiable): the KI **proposes**; `ValidatePatch` is the
dry-run the user sees, and only after confirmation does the job call `PatchEntity`
(the P25 patch path) to write. No tool bypasses the ownership check.
"""
from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from typing import Any

from photofant.inference.capabilities import Capability
from photofant.knowledge.schema import Owner
from photofant.knowledge.service import KnowledgeService


@dataclass
class Tool:
    """A named action bound to a `KnowledgeService`, exposed to a capability."""

    name: str
    description: str
    run: Callable[..., Any]


# Which tools each capability is allowed to use. INTERVIEW is deliberately
# read/search-free: a private person is built only from the interview answers.
_CAPABILITY_TOOLS: dict[Capability, tuple[str, ...]] = {
    Capability.TEXT_GENERATION: (),
    Capability.KNOWLEDGE_IMPORT: ("SearchKnowledge", "ReadMarkdown", "ValidatePatch", "PatchEntity"),
    Capability.KNOWLEDGE_UPDATE: ("SearchKnowledge", "ReadMarkdown", "ValidatePatch", "PatchEntity"),
    Capability.INTERVIEW: ("ValidatePatch", "PatchEntity"),
}


class ToolRegistry:
    """Builds the concrete tools over a `KnowledgeService` and hands out the
    allowed subset per capability. `owner` is the write attribution for this
    session's patches (P27 autonomy → inferred/web; never `user`)."""

    def __init__(self, service: KnowledgeService, owner: Owner) -> None:
        self._service = service
        self._owner = owner
        self._tools: dict[str, Tool] = {
            "SearchKnowledge": Tool(
                name="SearchKnowledge",
                description="Suche Entities per Freitext (optional Typ/Domäne). Liefert id, Titel, Typ.",
                run=self._search_knowledge,
            ),
            "ReadMarkdown": Tool(
                name="ReadMarkdown",
                description="Lies den Markdown-Text (Body) einer Entity per id oder Alias.",
                run=self._read_markdown,
            ),
            "ValidatePatch": Tool(
                name="ValidatePatch",
                description="Prüfe ein vorgeschlagenes Patch gegen die Domäne — ohne zu schreiben. Leere Liste = valide.",
                run=self._validate_patch,
            ),
            "PatchEntity": Tool(
                name="PatchEntity",
                description="Wende ein bestätigtes Patch an (über den Ownership-Pfad). Schreibt Markdown-first.",
                run=self._patch_entity,
            ),
        }

    def tools_for(self, capability: Capability) -> list[Tool]:
        names = _CAPABILITY_TOOLS.get(capability, ())
        return [self._tools[name] for name in names]

    def _search_knowledge(
        self, query: str, type: str | None = None, domain: str | None = None
    ) -> list[dict[str, str]]:
        entities = self._service.search_entities(query, type=type, domain=domain)
        return [{"id": entity.id, "title": entity.title, "type": entity.type} for entity in entities]

    def _read_markdown(self, entity_id: str) -> str:
        entity = self._service.find_entity(entity_id)
        return entity.body if entity is not None else ""

    def _validate_patch(self, entity_id: str, patch: dict[str, Any]) -> list[str]:
        return self._service.validate_patch(entity_id, patch)

    def _patch_entity(self, entity_id: str, patch: dict[str, Any]) -> dict[str, str]:
        entity = self._service.update_entity(entity_id, patch, self._owner)
        return {"id": entity.id, "title": entity.title, "type": entity.type}
