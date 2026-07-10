# STATE

**Kein aktiver Plan.** P26 (Empfehlungs-Engine) ist komplett und archiviert
(`docs/archive/2026-07/2026-07-01_p26-recommendation-engine/`).

## Backlog (offen zur Auswahl)

- `docs/planning/2026-07-01_p27-gemma-integration/` — KI-Layer/Gemma + Import/Update/Interview-Jobs.
- `docs/planning/2026-07-06_p34-mcp-wissensbasis/` — Entities/Beziehungen, Media-Links/Aufgaben,
  Lore/Empfehlungen, agentischer Workflow (Abhängigkeiten P24–P26 jetzt erfüllt).

## Smoke-Test P26 ausstehend (User)

Vor dem nächsten Plan lohnt sich ein kurzer Real-Check der Empfehlungs-Engine — die
Scoring-Gewichte sind der wackligste Punkt im ganzen Feature (Reason-Chain macht
Fehlgewichtung sichtbar, aber nur an echtem Bildmaterial):

1. Bild in der Lightbox öffnen → unter dem Lore-Panel erscheinen Empfehlungs-Karten mit
   Score-Badge + Begründungszeilen (CLIP + mind. ein Graph-Signal an einem Bild mit
   verknüpfter Person).
2. „Warum?"-Icon auf einer Empfehlungs-Karte → Popover zeigt Score + Begründungen.
3. „Warum nicht?"-Icon auf einer Karte in „Ähnliche Bilder" → Popover zeigt vorhandene +
   fehlende Signale gegen die Schwelle.
4. Nach einer Bio-Korrektur im Lore-Panel: „Warum geändert?"-Icon neben der Kurzbio →
   Popover zeigt Grund/Quelle/Zeit/Job aus der Korrektur-Historie.
5. `recommendations.enabled=false` in `settings.json` → Empfehlungs-Sektion entfällt komplett.

Details/volle Checkliste: `docs/archive/2026-07/2026-07-01_p26-recommendation-engine/README.md`.

## Nächster Schritt

Welchen Plan als Nächstes umsetzen? P27 (Gemma/KI-Layer) oder P34 (MCP-Wissensbasis) —
oder erst der Smoke-Test oben.
