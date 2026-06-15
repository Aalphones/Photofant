# P10 · Phase 2 — Trainingssets & Statistiken

> Rating: standard · Status: pending

## Kontext (vorher lesen)

- [README.md](README.md) — Kontrakt (settings, stats)
- [Konzept](../../Konzept-Photofant.md) **§9 komplett**
- `docs/design/js/training.jsx`

## Akzeptanzkriterien

- Trainingsset anlegen/füllen (Bulk-Bar „Zu Trainingsset", aus Album klonen); `settings` (trigger_word, prefix, suffix, split_ratio) editierbar.
- Stats-Endpoint + Dashboard: Framing-Verteilung, Tag-Häufigkeiten (Top-N), Qualitäts-Histogramm, AR-Bucket-Verteilung (Kohya-Buckets: 512/768/1024-Basen — Bucket-Logik dokumentieren), Near-Dupe-Quote (pHash über das Set).
- Set-Items zeigen effektive Caption (Override > Original) mit Editier-Möglichkeit pro Bild.
- Auto-Tagging/Captioning aus dem Set heraus (Rerun-Strecke aus P5 mit Set-Scope).

## Checkliste

- [ ] training_set-Kind aktivieren + Settings-Editor
- [ ] Stats-Aggregationen (SQL + pHash-Paarlauf, gecacht pro Set-Stand)
- [ ] Trainingssets-View (Dashboard + Item-Grid mit Caption-Edit)
- [ ] Rerun-Verdrahtung mit Set-Scope
- [ ] Doc-Update: routes.md, docs/models.md (settings-JSON)

## Report-Back
