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

- [ ] ADR-008 anlegen
- [ ] ADR-002/-003 Status/Fußnoten
- [ ] code-map.md / routes.md / models.md
- [ ] AGENTS.md Stack-Zeile (+ Konzept-Hinweis)
- [ ] design-reconciliation.md

## Report-Back
_(beim Umsetzen füllen)_
