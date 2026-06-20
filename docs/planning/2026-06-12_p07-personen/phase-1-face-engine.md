# P7 · Phase 1 — Face-Engine

> Rating: standard · Status: complete

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

- [x] Migration + FaceDto
- [x] `FaceEngine`-Implementierung (Detection, Alignment, Embedding, Age)
- [x] Crop-Logik (Padding, Dateinamen-Schema) + Face-Thumbnails
- [x] Job + Ledger-Integration + Detail-Panel-Strip
- [x] Doc-Update: docs/models.md (face)

## Report-Back

Implementiert 2026-06-20. Alle 5 Checklistenpunkte abgehakt.

**Abweichungen / Findings:**
- `source_version_id` in `face`-Tabelle als plain INTEGER (kein FK), da `version`-Tabelle erst P8 kommt — SQLite würde sowieso nicht prüfen, aber Alembic schlägt andernfalls an.
- buffalo_l-Adapter verwendet `PIL.Image.transform()` für affine Alignment statt OpenCV (keine zusätzliche Abhängigkeit).
- `age`-Feld im 64×64-Blob: genderage-Modell erwartet dieselbe Normierung wie ArcFace (127.5/128) — laut InsightFace-Quellcode korrekt.
- Face-Thumbnail-Größe fixiert auf 256 px (konfigurierbar später); Detail-Panel zeigt 72×72-Crops in der UI.
- `faces_done`-Flag war bereits im Ledger vorbereitet (0002-Migration), kein Schema-Delta nötig.
