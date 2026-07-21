# ADR-031 — Web-Recherche: einziger erlaubter Netzwerkzugriff der Wissensbasis

**Status:** Akzeptiert — 2026-07-21
**Querverweise:** [025](025-knowledge-vault-markdown-wahrheit.md) ·
[027](027-ai-capability-layer.md) · [028](028-gemma-runtime.md) ·
Konzept-ADR-009 (privat/öffentlich-Trennung, in `docs/Konzept-Agentic-Knowledge-Base/` —
nicht die gleichnamige Nummer unter `docs/decisions/`)

## Kontext
P27 legt zwei Kernregeln fest: (1) Gemma schreibt nie ohne Nutzer-Bestätigung, (2) keine
Laufzeit-Netzwerkzugriffe (Offline-Garantie). Die Web-Recherche braucht Regel (2) bewusst
anders. Regel (1) bleibt unangetastet — ein früherer Entwurf sah Auto-Write ohne Rückfrage
vor, der wurde am 2026-07-21 zugunsten des Bestätigungs-Wegs verworfen.

## Entscheidung
Eine neue, einzelne Capability (`KNOWLEDGE_DISCOVERY`) darf bei explizitem User-Klick pro
Entity einen Web-Suchaufruf machen. Ihr Ergebnis sind **Vorschläge**, keine Schreibungen:
die Fakten werden dem Nutzer zum Abhaken vorgelegt, erst die Bestätigung schreibt — mit
`owner=web` (niedrigste Schreibpriorität außer `inferred`, überschreibt nie `user`/`manual`).
Alle anderen P27-Capabilities (`KNOWLEDGE_IMPORT`, `KNOWLEDGE_UPDATE`, `INTERVIEW`) bleiben
offline. Private Domänen sind von `KNOWLEDGE_DISCOVERY` vollständig ausgeschlossen (Guard
wie `import-suggestion`).

## Betrachtete Optionen
- **Auto-Write ohne Rückfrage** (ursprünglicher Entwurf) — weniger Klicks, aber halluzinierte
  Fakten landen ungeprüft in der Ablage und die P27-Kernregel bekäme eine Ausnahme, die
  später jeder als Präzedenzfall zitiert. Verworfen.
- **Netzwerkzugriff generell erlauben** — würde die Offline-Garantie als Ganzes aufweichen.
  Verworfen: der Zugriff bleibt an genau diese eine Capability und einen expliziten Klick
  gebunden.

## Konsequenzen
- Jede bestätigte Übernahme erzeugt Changelog-Einträge + trägt Quell-URLs in
  `entity.sources` — nachvollziehbar, wo ein Wert herkommt.
- `ai.autonomy.discovery` (Default `off`) ist der einzige globale Schalter; ohne ihn explizit
  auf `auto` zu stellen, macht die Anwendung weiterhin keinen einzigen Netzwerkzugriff aus
  der Wissensbasis heraus.
- Kein Agenten-Loop: die Suche läuft deterministisch vor dem Gemma-Call, kein
  Function-Calling (siehe P38-README „Wichtige Funde").
