# P9 · Phase 3 — Upscale

> Rating: standard · Status: pending

## Kontext (vorher lesen)

- [README.md](README.md) — Kontrakt (upscale-Endpoint)
- [Konzept](../../Konzept-Photofant.md) §8.1, §8.3 (Upscale-Sonderfall im Face-Dedupe), §12.3/§12.4 (SeedVR2-Varianten)
- ADR-002, P8 Phase 4/5 (Versionierung, Dedupe)

## Akzeptanzkriterien

- SeedVR2 über die GenerativeEngine: Upscale als Queue-Job, Ergebnis als Version (`type = upscale`), `is_current`-Tausch wie im Konzept („tauscht Foto gegen Upscale", rückgängig machbar).
- Face-Dedupe-Upscale-Regel aktiv: visuell gleicher Crop mit klar höherer Auflösung → behalten, `is_upscaled = true`, alter Crop als überholt markiert.
- Bulk-Upscale über die Bulk-Edit-Strecke; VRAM-Schutz: ein generativer Job zur Zeit (Queue-Klasse).
- Editor-Tool „Upscale" (Modell-/Varianten-Anzeige, Faktor falls vom Modell geboten — Capabilities-Descriptor).

## Checkliste

- [ ] SeedVR2-Integration (Variante nach Registry, GGUF/fp8-Ladepfad aus ADR-002)
- [ ] Endpoint + Job (Serien-Schutz, Fortschritt)
- [ ] Dedupe-Regel scharf schalten (P8-Flagge)
- [ ] Editor-Tool + Bulk-Verdrahtung
- [ ] Doc-Update: routes.md

## Report-Back
