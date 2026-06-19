# FINDINGS

Format: `- [ ] → Phase N: <Erkenntnis / Abweichung / Nachfolge-Task>`

- [x] → Phase 2 (erledigt): `ProcessingConfig` in `@photofant/models` (`config.model.ts`) statt in `models.reducer.ts` definiert — Actions und Reducer importieren beide von dort, sonst Kreisabhängigkeit.
