# FINDINGS — P21 Galerie-Stapel & Tab-Konsolidierung

Format: `- [ ] → Phase N: <Erkenntnis / Abweichung / Folgefund>`

<!-- Einträge werden während der Umsetzung von mode-implementing eingepflegt -->

- [x] → Phase 1: ComfyUI-Default-Import legte bisher immer eine `Version`, nie ein Asset an —
  Kontrakt-Annahme "original_id-Kinder laufen schon durch die Pipeline" war falsch.
  Korrigiert via ADR-013 (siehe README + phase-1 Update). Wird in Phase 1 selbst gebaut.
- [ ] → Phase 2/3: Galerie-Grid muss beachten, dass frisch umgestellte ComfyUI-Edits jetzt
  als vollwertige Asset-Kacheln erscheinen (nicht mehr im `edits`-Tab-Modell), inkl. eigener
  Tags/Caption/Faces sichtbar in der Detailansicht — keine Sonderbehandlung nötig, aber beim
  Testen im Blick behalten.
