# P7 · Phase 1 — Face-Engine

> Rating: standard · Status: pending

## Kontext (vorher lesen)

- [README.md](README.md) — Kontrakt (FaceDto)
- [Konzept](../../Konzept-Photofant.md) §5 (face-Tabelle), §7 (buffalo_l, Extraktion mit Padding)
- P5 Phase 1 (Inferenz-Layer — `FaceEngine`-Interface dort einhängen)

## Akzeptanzkriterien

- Migration: `face`-Tabelle nach Konzept §5.
- `buffalo_l` über die Registry/den Inferenz-Layer: Detection (BBoxes + Landmarks), ArcFace-Embedding, Age; Crop mit konfigurierbarem Padding nach `personX/faces/` (vorerst `_unknown/faces/`).
- Face-Job im Import-Fluss (Ledger `faces_done`); pHash pro Crop (für §8.3/Dupes).
- Detail-Panel: Gesichter-Strip (Crop-Thumbs + Score/Age) nach Prototyp; Thumbnails für Faces in der Cache-DB (`target_kind = face`).

## Checkliste

- [ ] Migration + FaceDto
- [ ] `FaceEngine`-Implementierung (Detection, Alignment, Embedding, Age)
- [ ] Crop-Logik (Padding, Dateinamen-Schema) + Face-Thumbnails
- [ ] Job + Ledger-Integration + Detail-Panel-Strip
- [ ] Doc-Update: docs/models.md (face)

## Report-Back
