# P9 · Phase 3 — Upscale

> Rating: standard · Status: complete

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

- [x] SeedVR2-Integration (Variante nach Registry — seedvr2 pkg → spandrel → PIL Lanczos fallback)
- [x] Endpoint + Job (`POST /api/assets/{id}/upscale` + `upscale_job.py`, Generative-Availability-Check)
- [x] Dedupe-Regel scharf schalten — `_apply_face_dedupe_upscale_rule` setzt `origin_type='superseded_by_upscale'` auf alten Face-Crops
- [x] Editor-Tool + Bulk-Verdrahtung (Lightbox-Button + `POST /api/assets/bulk-upscale`)
- [x] Doc-Update: routes.md

## Report-Back

- `backend/photofant/inference/seedvr2_upscaler.py` — SeedVR2Upscaler (drei Backends: seedvr2 pkg / spandrel / PIL Lanczos)
- `backend/photofant/jobs/upscale_job.py` — Queue-Job, Version-Erstellung, Face-Dedupe-Regel
- `backend/photofant/api/assets.py` — `POST /{id}/upscale` + `POST /bulk-upscale`
- `backend/photofant/media/ops.py` — `upscale`-Op für Bulk-Edit-Strecke
- `backend/photofant/jobs/queue.py` — `UPSCALE` JobKind
- `frontend/src/app/services/generative.service.ts` — GenerativeService
- `frontend/src/app/features/galerie/lightbox/lightbox.ts+html+scss` — Upscale-Button (capabilities-gegated)
