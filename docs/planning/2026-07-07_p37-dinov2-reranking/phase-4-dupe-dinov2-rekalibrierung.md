# Phase 4 — Dupe-Scan auf DINOv2 + Schwellwert-Rekalibrierung

**Komplexität:** standard · **Status:** pending

## Kontext (vor dem Bauen lesen)
- `backend/photofant/jobs/dupe_scan_job.py` — der Duplikat-Scan (`np.stack` über die Embedding-BLOBs, Cosine gegen
  `dupe_clip_threshold`). Wird von SigLIP2 auf **DINOv2** umgestellt: liest `dino_embedding` + `vec_asset_dino`.
- `backend/photofant/settings.py` — `dupe_clip_threshold`, `training_near_dupe_clip_threshold`, das `_LEGACY`/
  `_MIGRATED`-Settings-Migrations-Muster. Neu: `dupe_dino_threshold`.
- `backend/photofant/api/duplicates.py`, `api/review.py` — Konsumenten der Dupe-Ergebnisse (Anzeige). Prüfen, ob die
  Prozent-/Distanz-Darstellung modell-agnostisch ist oder einen SigLIP-spezifischen Bezug hat, der mitzieht.

## Warum DINOv2 hier Primär-Signal ist
Ein Duplikat ist definiert über **visuelle Erscheinung**, nicht über Inhalt — genau DINOv2s Stärke (State-of-the-Art
für Near-Dupe/Copy-Detection). SigLIP2 würde auch inhaltlich Ähnliches („zwei verschiedene rote Autos") zu nah
einsortieren. Der Scan läuft daher künftig **ausschließlich** auf DINOv2-Vektoren. Der SigLIP2-Dupe-Schwellwert
(`dupe_clip_threshold`) bleibt als inerter Settings-Key erhalten (Rollback, falls die Umstellung zurückgedreht wird).

## Ablauf (überwiegend Umstellung + Messung)
1. `dupe_scan_job` auf `dino_embedding` / `vec_asset_dino` umstellen; Schwellwert-Bezug auf `dupe_dino_threshold`.
2. Nach einem Reembed mit aktivem DINOv2 (Phase 2): „Duplikate scannen (vollständig)" auslösen.
3. An bekannten echten Duplikaten prüfen, wo DINOv2 sie in der Cosine-Distanz einsortiert → `dupe_dino_threshold`
   justieren, bis echte Dupes treffen und Fremdpaare draußen bleiben. **Neuer Distanzbereich als bei CLIP/SigLIP** —
   Wert von Grund auf empirisch bestimmen, nicht vom alten übernehmen.
4. `training_near_dupe_clip_threshold`-Äquivalent für DINOv2 gegenprüfen, falls der Trainings-Near-Dupe-Pfad ebenfalls
   auf DINOv2 soll (entscheiden + in FINDINGS festhalten).

## AK der Phase
- [ ] `dupe_scan_job` nutzt DINOv2-Vektoren + `dupe_dino_threshold`; SigLIP2 wird für den Scan nicht mehr gelesen.
- [ ] `dupe_dino_threshold` als Settings-Key mit empirisch bestimmtem Default; über die Einstellungen-UI einstellbar.
      Begründung des Werts im Report-Back.
- [ ] Duplikat-Scan findet bekannte echte Duplikate zuverlässig, ohne Fremdpaare zu fluten (Smoke #2).
- [ ] Anzeige (`api/duplicates.py`, `api/review.py`) zeigt korrekte Distanzen/Prozente für das DINOv2-Signal.
- [ ] `ruff check .` grün; Tests grün.

## Doc-Updates
- [ ] `docs/decisions/024-two-stage-rerank.md` — Abschnitt „Duplikat-Scan auf DINOv2" mit End-Schwellwert + Begründung.
- [ ] `docs/models.md` / `docs/code-map.md` — Dupe-Scan-Signalquelle aktualisieren (SigLIP2 → DINOv2).
- [ ] STATE.md auf `(kein aktiver Plan)` bzw. nächsten Plan zeigen lassen; P37 nach `docs/archive/2026-07/` verschieben.

## Report-Back
