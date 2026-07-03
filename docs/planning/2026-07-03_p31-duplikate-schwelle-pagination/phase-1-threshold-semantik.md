# Phase 1 — Threshold-Semantik & Entkopplung

## Kontext (vor Umsetzung lesen)

- `backend/photofant/settings.py` — Defaults, Typ-Validierung, Load/Save
- `backend/photofant/jobs/dupe_scan_job.py` — Voll-Scan (pHash exakt + CLIP mit Threshold)
- `backend/photofant/api/duplicates.py` — Per-Person-Suche, eigene Clamp-Konstanten
- `backend/photofant/api/review.py` — `get_similar_assets` (Lightbox, nutzt heute denselben Key)
- `frontend/src/app/models/config.model.ts` + `store/models/models.effects.ts` — Settings-Mapping
- `frontend/src/app/features/einstellungen/verarbeitung/` — Slider-UI (70–99%)
- Konventionen: `docs/conventions/python.md`, `docs/conventions/angular.md`

## Abnahmekriterien

1. Frische Installation: `dupe_clip_threshold` = 0.03; bestehende `settings.json` mit exakt
   0.15 wird einmalig auf 0.03 migriert (jeder andere Wert bleibt unangetastet).
2. Neuer Key `similar_clip_threshold` (Default 0.15); Lightbox `get_similar_assets` nutzt ihn
   statt `dupe_clip_threshold` — Lightbox-Verhalten bleibt faktisch unverändert.
3. Per-Person-Suche (`api/duplicates.py`): Clamp-Untergrenze 0.01 statt 0.05, Request-Default
   liest den Settings-Default statt hartem 0.15 — ein 0.03-Setting wird nicht mehr auf 0.05
   hochgeclampt.
4. Voll-Scan löscht zu Beginn (nur `scope != "selection"`) alle ungelösten
   `dupe_candidate`-ReviewItems, bevor er neue einfügt.
5. Settings-Slider: `min="90" max="99"`, Default zeigt 97%; Erklärtext nennt den neuen Bereich
   (z.B. „99 % = nur nahezu identische Bilder · 90 % = auch stärker bearbeitete Varianten").
   Erklärungs-Affordance bleibt in-place (Sub-Text wie bisher).
6. `ruff check` grün; bestehende Backend-Tests grün.

## Checkliste

- [x] `settings.py`: Default `dupe_clip_threshold` → 0.03; neuer Key `similar_clip_threshold`
      (float, Default 0.15) inkl. Typ-Map
- [x] `settings.py` (Load-Pfad): einmalige Migration — persistierter Wert exakt 0.15 → 0.03
      schreiben, kurzer `log.info`
- [x] `api/review.py` `get_similar_assets`: `similar_clip_threshold` statt `dupe_clip_threshold`
- [x] `api/duplicates.py`: `_MIN_CLIP_THRESHOLD = 0.01`; Request-Default liest jetzt
      `settings["dupe_clip_threshold"]` statt hartem 0.15 (Konstante `_DEFAULT_CLIP_THRESHOLD`
      entfernt, da überflüssig)
- [x] `jobs/dupe_scan_job.py`: Purge ungelöster `dupe_candidate`-Items am Anfang des Voll-Scans
      (ein DELETE, vor dem Vergleich; Selection-Scope purgt nicht)
- [x] Frontend `config.model.ts`: `dupeClipThreshold`-Default 0.03 (Anzeige-Fallback)
- [x] Frontend `verarbeitung.html`: Slider `min="90"`, Erklärtext aktualisiert
- [x] Doc-Update: grep `dupe_clip_threshold` in `docs/` geprüft — nur eigener Plan +
      ADR-007 (historische Entscheidung, bewusst nicht rückwirkend geändert) betroffen
- [x] `uv run ruff check .` (nur die vier geänderten Dateien: sauber; Repo-weite Findings sind
      Altlasten in unbeteiligten Dateien) + Backend-Tests (12 Fehler — allesamt vorbestehend,
      per `git stash` verifiziert: comfyui_run-Signaturmismatch + ein caption_config-Test,
      keine dupe/settings/review-Tests existieren)

## Report-Back

Threshold-Semantik entkoppelt: Voll-Scan-Duplikate (`dupe_clip_threshold`, jetzt 0.03 ≙ 97 %)
und Lightbox-„Ähnliche Bilder" (neuer Key `similar_clip_threshold`, unverändert 0.15) laufen
über getrennte Settings. Migration hebt einen exakt unveränderten Alt-Default automatisch auf
den neuen Wert. Per-Person-Duplikat-Check clamped nicht mehr fälschlich auf 0.05 hoch und
übernimmt den Settings-Default statt eines hartcodierten Werts. Voll-Scan löscht vor jedem
Lauf alte ungelöste Kandidaten. Slider-UI zeigt 90–99 % mit angepasstem Erklärtext.
