# Phase 6 — Docs + ADR

**Rating:** mechanisch (Dokumentation nachziehen)

## Kontext (lesen)

- [docs/decisions/002-generatives-backend.md](../../../docs/decisions/002-generatives-backend.md)
- [docs/decisions/003-comfyui-trigger-integration.md](../../../docs/decisions/003-comfyui-trigger-integration.md)
- [docs/code-map.md](../../../docs/code-map.md), [docs/routes.md](../../../docs/routes.md), [docs/models.md](../../../docs/models.md)
- [AGENTS.md](../../../AGENTS.md), [docs/design-reconciliation.md](../../../docs/design-reconciliation.md)

## Akzeptanzkriterien

1. **ADR-008** (`docs/decisions/008-generativ-via-comfyui.md`): Kontext (ADR-002 vs. P16),
   Optionen, Entscheidung „ComfyUI als einziger generativer Pfad, P9 entfernt", Konsequenzen.
   Verweist auf ADR-002 (ersetzt) und ADR-003 (erweitert).
2. **ADR-002** Status auf „Ersetzt durch ADR-008" + Fußnote. **ADR-003** Fußnote: P8b ist jetzt
   der einzige Generativ-Pfad; Gating-/Koexistenz-Passagen, die P9 erwähnen, korrigiert.
3. **code-map.md:** Generativ-Zeile umgeschrieben (P9-Dateien weg, alles ComfyUI), ComfyUI-Zeile
   um FS-Discovery/3-Aufgaben aktualisiert.
4. **routes.md / models.md:** entfallene Generativ- und ComfyUI-CRUD-Routen + gedroppte Tabelle
   nachgezogen (mit Phase 2/3 synchron).
5. **AGENTS.md:** Stack-Zeile „Inferenz" — torch/diffusers-Generativ raus; ComfyUI als
   Generativ-Pfad. Konzept-Doc bei direktem Widerspruch mit Kurzhinweis markiert.
6. **design-reconciliation.md:** Editor-Mockup-Diskrepanz (überholte Upscale/Flux-Panels) als
   bewusste Abweichung dokumentiert.

## Checkliste

- [x] ADR-008 anlegen
- [x] ADR-002/-003 Status/Fußnoten
- [x] code-map.md / routes.md / models.md
- [x] AGENTS.md Stack-Zeile (+ Konzept-Hinweis)
- [x] design-reconciliation.md

## Report-Back

- **ADR-008** angelegt mit Kontext, Optionen, Entscheidung, Architektur-Diagramm, Kontrakt-Sektion und Konsequenzen. Prompt-Erkennung ohne Single-Encode-Fallback dort dokumentiert.
- **ADR-002** Status auf „Ersetzt durch ADR-008" + Fußnote.
- **ADR-003** Entscheidungs-Tabelle korrigiert (P9 durchgestrichen, ComfyUI = einziger Pfad), P9-Koexistenz-Passage + Konsequenzen als überholt markiert.
- **code-map.md** ComfyUI-Integration-Zeile um FS-Discovery + 3-Default-Zuordnungen ergänzt. Generativ-Zeile war bereits korrekt (Phase 5 hatte sie angepasst).
- **routes.md** geprüft: RunRequest bereits korrekt, CapabilitiesDto bereits korrekt — kein P9-Rückstand. Keine Änderung nötig.
- **models.md** `version.type` um `comfyui` erweitert, P9-Typen (`upscale|flux_edit|inpaint`) als historisch/Legacy markiert. `comfyui_workflow` war bereits als dropped dokumentiert.
- **AGENTS.md** Stack-Zeile Inferenz: diffusers entfernt, ComfyUI als einziger Generativ-Pfad + ADR-008-Verweis.
- **design-reconciliation.md** Editor-Generativ-Sektion war bereits von Phase 5 gepflegt (bewusste Abweichung inkl. ADR-008-Verweis).
