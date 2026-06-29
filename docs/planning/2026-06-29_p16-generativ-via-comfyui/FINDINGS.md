# FINDINGS — P16 Generativ via ComfyUI

Getaggte Erkenntnisse während der Umsetzung. Format:

- [ ] → Phase N: <Erkenntnis / Abweichung / offene Frage>

---

- [ ] → Phase 3: Vollständiger P9-Anhängsel-Sweep (Klassifikation gehört-zu-P9 / bleibt) hier ablegen, bevor gelöscht wird.
- [ ] → Phase 6 (Doku): Prompt-Erkennung nur via Titel-Match (Positive/Negative). Der „Single-Encode-Fallback" (genau ein CLIPTextEncode → positiv, AK1) wurde weggelassen — er kollidiert mit SeedVR2, wo das einzige CLIPTextEncode ein interner Upscaler-Prompt ist. Bewusste Entscheidung: Nutzer benennen Nodes explizit mit Positive/Negative, sonst kein Prompt-Feld. In ADR-008 oder Design-Reconciliation vermerken.
