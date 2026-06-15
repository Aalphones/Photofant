# P8 · Phase 3 — rembg & Smart-Crop

> Rating: standard · Status: pending

## Kontext (vorher lesen)

- [README.md](README.md) — Kontrakt
- [Konzept](../../Konzept-Photofant.md) §8.1 (rembg, Smart-Crop)
- Inferenz-Layer (P5 Phase 1), Face-Engine (P7 Phase 1 — falls schon umgesetzt)

## Akzeptanzkriterien

- rembg (ONNX über Registry, gated): Hintergrund entfernen → PNG mit Alpha als Step; Vorschau zeigt Schachbrett-Transparenz.
- Smart-Crop: zentriert auf erkanntes Gesicht (Face-BBox + gewählte Ratio). **Wenn P7 noch nicht umgesetzt ist:** Tool ausblenden mit Gating-Hinweis „benötigt Personen-Erkennung" — kein Fake-Fallback.
- Beide Ops bulk-fähig (Phase 5 nutzt das).

## Checkliste

- [ ] rembg-Op über den Inferenz-Layer (Modell-Gating beachten)
- [ ] Smart-Crop-Op (BBox-Quelle: vorhandene Faces oder On-the-fly-Detection, je nach P7-Stand)
- [ ] Tool-Panels + Gating-Hinweise
- [ ] Doc-Update: keiner über routes.md hinaus

## Report-Back
