# P8 · Phase 3 — rembg & Smart-Crop

> Rating: standard · Status: complete

## Kontext (vorher lesen)

- [README.md](README.md) — Kontrakt
- [Konzept](../../Konzept-Photofant.md) §8.1 (rembg, Smart-Crop)
- Inferenz-Layer (P5 Phase 1), Face-Engine (P7 Phase 1 — falls schon umgesetzt)

## Akzeptanzkriterien

- rembg (ONNX über Registry, gated): Hintergrund entfernen → PNG mit Alpha als Step; Vorschau zeigt Schachbrett-Transparenz.
- Smart-Crop: zentriert auf erkanntes Gesicht (Face-BBox + gewählte Ratio). **Wenn P7 noch nicht umgesetzt ist:** Tool ausblenden mit Gating-Hinweis „benötigt Personen-Erkennung" — kein Fake-Fallback.
- Beide Ops bulk-fähig (Phase 5 nutzt das).

## Checkliste

- [x] rembg-Op über den Inferenz-Layer (Modell-Gating beachten)
- [x] Smart-Crop-Op (On-the-fly-Detection via SCRFD, P7 ist live)
- [x] Tool-Panels + Gating-Hinweise
- [x] Doc-Update: routes.md (rembg + smart_crop Op-Params)

## Report-Back

- **rembg:** `_apply_rembg` in `media/ops.py` — u2net ONNX, 320×320 ImageNet-Normalisierung, Alpha-Maske; `ModelNotAvailableError` wird in `edit_sessions.py` zu HTTP 422 `MODEL_UNAVAILABLE`.
- **smart_crop:** `_apply_smart_crop` — nur SCRFD (kein ArcFace/Age), Crop 3× Gesichtsgröße zentriert auf bestes Face. Falls kein Gesicht erkannt: Bild unverändert.
- **Frontend:** `capabilities`-Signal aus `modelsSelectors` in `Editor` dispatcht `loadCapabilities()` beim Init; `BasisPanel` bekommt Capabilities als Input, zeigt Gating-Hinweise für `faces === false` (Smart-Crop) und `rembg === false` (neuer Rembg-Abschnitt).
- **Ruff-Fixes:** 5 pre-existing Fehler in `buffalo_l.py`, `face_job.py`, `import_job.py` bereinigt.
