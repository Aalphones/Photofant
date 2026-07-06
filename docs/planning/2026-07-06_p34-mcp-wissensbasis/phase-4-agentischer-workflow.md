# Phase 4 — Agentischer Wissens-Workflow (Domänen-Kontext)

**Komplexität:** mechanisch · **Unterbau:** P23 (Task-Queue, Phase 2) · **Status:** pending

## Zweck

Die Tools der Phasen 1–3 sind vorhanden — diese Phase macht daraus einen **nutzbaren Workflow**, ohne
dass der Agent die Domänen-Struktur raten muss. Sie fügt **keinen** neuen Datenpfad hinzu, nur Kontext:
Der Agent versteht, wie er die Wissens-Aufgaben eigenständig abarbeitet (Aufgabe holen → Kontext lesen
→ Entity anlegen/patchen → Aufgabe auflösen). Damit ersetzt/ergänzt ein externer Agent die interne
Gemma-Wissenspflege (P27) über die Cloud/ein Fremd-LLM.

## Kontext (vor dem Bauen lesen)

- `README.md` + `phase-1..3` — die vorhandenen Wissens-Tools.
- `2026-07-01_p22-knowledge-engine/README.md` — Domänen-Config (`domains/<domain>.yaml`: Entity-Types +
  Relationship-Types), Entity-Frontmatter.
- MCP Python SDK — Prompt-Registrierung (`@mcp.prompt`), falls genutzt; sonst reicht eine ausführliche
  Tool-Description am Einstiegs-Tool.

## AK (falsifizierbar)

- [ ] Ein MCP-Prompt (oder, falls Prompts nicht genutzt werden, ein Tool `knowledge_workflow_guide()`)
      liefert dem Agenten den Domänen-Kontext: verfügbare Typen/Relationship-Typen (aus `list_domains`),
      die Ownership-Regel in einem Satz, und den Standard-Ablauf „Aufgabe → Kontext → Entity → auflösen".
- [ ] `next_knowledge_task()` — Komfort-Tool: liefert die älteste offene Aufgabe samt aufgelöstem Kontext
      (z. B. bei `kind=new_person`: Person-Name + Beispiel-Asset-IDs), damit der Agent nicht erst
      `list_knowledge_tasks` + Einzelabfragen kombinieren muss.
- [ ] Der Workflow ist ohne weitere Erklärung durchführbar: Ein Agent kann allein aus Prompt + Tool-
      Descriptions eine offene „neue Person"-Aufgabe zu einer verknüpften Entity machen.

## Umsetzung — Checkliste

- [ ] `mcp/prompts/knowledge.py` (oder Guide-Tool) mit Domänen-Kontext + Ablauf.
- [ ] `next_knowledge_task()` in `mcp/tools/knowledge.py`.
- [ ] Doc: `docs/routes.md` MCP-Wissens-Abschnitt final (alle Tools + Prompt gelistet),
      `docs/code-map.md` prüfen.

## Report-Back
