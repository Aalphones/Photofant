# P34 — MCP für die Wissensbasis (Follow-up zum MCP-Basisplan)

> Erweitert die lokale MCP-Schnittstelle (`2026-07-06_mcp-schnittstelle`) um Werkzeuge für die
> **agentische Wissensbasis** (P22–P27): ein externer MCP-Agent kann Entities durchsuchen, lesen,
> anlegen, ändern, verknüpfen, die Wissens-Aufgaben abarbeiten und Lore/Empfehlungen lesen — über
> **denselben `KnowledgeService`** wie die interne Gemma-KI, mit derselben Ownership-/Validator-Sicherung.
> *(private, lean.)*

## Kernidee — der MCP-Agent ist ein zweiter Wissens-Kopf

P27 gibt Gemma eine interne Capability-/Tool-Registry (`ReadMarkdown`, `SearchKnowledge`, `PatchEntity`),
mit der es Wissen pflegt — **nie per Direkt-Write, immer über `KnowledgeService` + Validator + Ownership**
(P27-Sicherheitsregel). Dieser Plan gibt einem **externen** Agenten dieselbe Fähigkeit über MCP. Der
externe Agent ist damit die Cloud-/Fremd-LLM-Alternative zu Gemma: Er füllt fehlendes Wissen, pflegt
Beziehungen, arbeitet die Aufgaben-Queue ab. **Er ruft Gemma nicht auf** (ein LLM auf dem anderen wäre
unsinnig) — er *ist* das LLM und nutzt dieselbe Service-Schicht darunter.

## Harte Voraussetzungen (dieser Plan ist erst dann umsetzbar)

- **MCP-Basisplan** `2026-07-06_mcp-schnittstelle` umgesetzt (liefert `mcp/server.py`, `mcp/adapter.py`,
  `mcp/gate.py`, Settings-Toggle, das Tool-Registrierungs-Muster). **Ohne ihn kein Fundament.**
- **P22** (Knowledge Engine: `KnowledgeService`, `api/knowledge.py`, Vault, Cache) → Phase 1.
- **P23** (Task-Queue) + **P24** (Media-Links) → Phase 2.
- **P25** (Lore-Aggregation) + **P26** (Recommendations) → Phase 3.

Jede Phase ist erst umsetzbar, wenn ihr Wissens-Unterbau steht. 🟡 **Das ist ein echter Backlog-Plan:**
Er wartet auf beide Stränge, kein Sofort-Start.

## Zentrale Entscheidung — Owner-Stufe für MCP-Wissens-Writes (ADR-020)

Ein externer Agent kann korrekt liegen (User dirigiert ihn) **oder** halluzinieren (wie Gemma). Die
Ownership-Regel aus P22 (`user > manual > web > inferred`, niedrigere überschreibt höhere nicht) ist
der Schutz. Entscheidung dieses Plans:

- **MCP-Wissens-Writes laufen durch denselben `KnowledgeService`-/Validator-/Ownership-Pfad** wie alles
  andere — **kein Bypass** (P27-Sicherheitsregel gilt auch für externe Agenten).
- Die zugewiesene `owner`-Stufe ist per Setting `mcp.knowledge_owner` konfigurierbar,
  **Default `manual`** (der User steuert den Agenten bewusst; user-Werte bleiben trotzdem geschützt).
- **Alternative** (im ADR dokumentiert): Default `inferred` — behandelt den Agenten als unsichere
  KI-Quelle, überschreibt fast nichts, sicherer aber der Agent kann kaum bestehendes Wissen korrigieren.
  `manual` gewählt, weil der Agent user-gesteuert ist und die Ownership-Regel den Rest absichert.

## Phasen-Übersicht

| Phase | Thema | Unterbau | Komplexität | Status |
|---|---|---|---|---|
| 1 | Entities, Beziehungen, Suche + Owner-Semantik | P22 | heikel | pending |
| 2 | Media-Links + Wissens-Aufgaben | P23, P24 | standard | pending |
| 3 | Lore + Empfehlungen (read) | P25, P26 | standard | pending |
| 4 | Agentischer Wissens-Workflow (Domänen-Kontext als MCP-Prompt) | P23 | mechanisch | pending |

## Kontrakt (Drift-Anker)

**Wo der Code wohnt** (erweitert das `mcp/`-Modul aus dem Basisplan):
```
backend/photofant/mcp/tools/knowledge.py   # alle Wissens-Tools dieses Plans
backend/photofant/mcp/prompts/knowledge.py # Phase 4: Domänen-Kontext als MCP-Prompt (falls SDK-Prompts genutzt)
```

**Tool → Backend-Aufruf:** identisch zum Basisplan — die Tools rufen die `api/knowledge.py`-Endpoint-
Funktionen über `mcp/adapter.py:run_endpoint()` auf (kein HTTP-Loopback, keine Doppel-Logik). Die
Endpoint-Signaturen stehen in den **Kontrakt-Sektionen von P22–P26** (nicht im Code, solange die Pläne
nicht umgesetzt sind — beim Umsetzen gegen den dann realen `api/knowledge.py` prüfen).

**Confirmation-Gate** (`mcp/gate.py` aus dem Basisplan): destruktive Wissens-Tools verlangen
`confirm: true` — `delete_entity`, `remove_relationship`, `unlink_entity`. `create_entity`/`update_entity`/
`patch_entity` brauchen **kein** Gate (Ownership-Regel schützt bestehende user-Werte; Fehlschreibungen sind
über den Vault-Changelog nachvollziehbar und korrigierbar).

**Rückgabe-Format:** knappes JSON (Entity-id, Titel, Typ, Confidence, Owner) — kein Roh-Markdown-Dump.
Listen auf `mcp.max_search_results` gedeckelt.

## settings.json — vorab freigeben

- `mcp.knowledge_owner` (enum `manual|web|inferred`, **default `manual`**) — Owner-Stufe für
  MCP-Wissens-Writes. Ein Dropdown in der bestehenden MCP-Settings-Sektion (Basisplan) + i-Tooltip, das
  die Ownership-Folge in einem Satz erklärt.

## Finale AK (Gesamt)

- [ ] Ein MCP-Agent findet eine Entity per Titel/Alias/Typ, liest sie, legt eine neue an, ändert ein Feld
      und verknüpft zwei Entities — alles landet **Markdown-first** im Vault (nicht nur im Cache).
- [ ] Ein Write mit niedrigerer Owner-Priorität als ein bestehender user-Wert wird abgelehnt (Ownership
      greift auch über MCP).
- [ ] Der Agent verknüpft eine Person/ein Asset mit einer Entity und liest die Verknüpfung zurück.
- [ ] Der Agent holt offene Wissens-Aufgaben, legt für eine die Entity an und löst die Aufgabe.
- [ ] Der Agent liest die Lore-Sicht und die Empfehlungen zu einem Bild (read-only).
- [ ] Destruktive Wissens-Tools verweigern ohne `confirm=true`.
- [ ] `docs/routes.md` (MCP-Abschnitt um Wissens-Tools), `docs/code-map.md`, ADR-020 aktuell.

## Smoke-Checkliste (du prüfst am Plan-Ende — Wackelstellen zuerst)

1. **(Owner-Semantik — unsicherste Stelle)** Per MCP-Agent ein user-gepflegtes Feld einer Entity mit
   `mcp.knowledge_owner=inferred` überschreiben wollen → wird abgelehnt; mit `=manual` und einem
   nicht-user-Feld → geht durch. `cat` der Vault-Datei zeigt Änderung + Changelog-Eintrag.
2. Agent legt Entity an → Markdown-Datei liegt unter `knowledge/<type>/…md`, Cache findet sie per Suche.
3. Agent verknüpft eine bestätigte Person mit der Entity → Personen-Detail zeigt `linked_entity`.
4. Agent holt offene Aufgaben (`list_knowledge_tasks`) → arbeitet eine ab → Aufgabe ist resolved.
5. `delete_entity` ohne `confirm` → verweigert mit Klartext; mit `confirm=true` → Datei weg.

## Risiken & offene Annahmen

- 🟡 **Owner-Semantik** (ADR-020) — falsche Default-Stufe = Agent überschreibt zu viel oder zu wenig.
  Unsicherste Stelle, Check siehe Smoke #1. Mitigation: Setting + Default `manual` + Ownership-Schutz.
- 🟡 **Kontrakt-Drift zu P22–P26** — dieser Plan referenziert Endpoint-Signaturen aus Plänen, die beim
  Schreiben noch nicht umgesetzt sind. Beim Umsetzen gegen den dann realen `api/knowledge.py` abgleichen;
  Abweichungen in `FINDINGS.md`.
- 🟡 **Halluzinierte Wissens-Writes** — ein Cloud-Agent erfindet Fakten. Mitigation: Ownership schützt
  user-Werte, Vault-Changelog macht jede Änderung nachvollziehbar/rückgängig, destruktive Ops mit Gate.
- 🟡 **Datenschutz verschärft** — der MCP-Basisplan warnt schon, dass Bilder/Metadaten bei einem Cloud-
  Agenten landen. Bei Wissens-Tools kommen **private Personen-Entities** (P27-ADR-009) dazu. Der bestehende
  Warnhinweis in der MCP-Settings-Sektion deckt das ab; eine Zeile dort um „…und dein Wissen" ergänzen.

## Konfidenz-Ausweis

1. **Owner-Semantik für externe Writes** (Phase 1) — siehe Smoke #1. Der Check klärt es.
2. **Adapter gegen `api/knowledge.py`** — sobald P22 real ist: `run_endpoint()` gegen `search_entities`
   testen (wie im Basisplan gegen `list_assets`). Trägt das, tragen alle Wissens-Tools.
3. Keine weiteren wackligen Stellen — die Tools sind dünne Adapter auf fertige Endpoints.

## ADR

- **ADR-020** — MCP-Wissens-Writes: über `KnowledgeService`/Validator/Ownership, kein Bypass; Owner-Stufe
  per Setting, Default `manual`. `docs/decisions/020-mcp-wissensbasis-ownership.md` (Phase 1 anlegen).
  Nächste freie: Platte bis 018, Basisplan reserviert 019 → 020.

## Bottom-Sektionen (beim Archivieren füllen)

### Summary
### Files touched
### Commits
### Deviations from plan
### Follow-ups
