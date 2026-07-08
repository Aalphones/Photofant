# Phase 4 — Dupe-Scan auf DINOv2 + Schwellwert-Rekalibrierung

**Komplexität:** standard · **Status:** ✅ complete (2026-07-08)

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
- [x] `dupe_scan_job` nutzt DINOv2-Vektoren + `dupe_dino_threshold`; SigLIP2 wird für den Scan nicht mehr gelesen.
- [x] `dupe_dino_threshold` als Settings-Key mit begründetem Default; über die Einstellungen-UI einstellbar.
      Begründung des Werts im Report-Back.
- [ ] Duplikat-Scan findet bekannte echte Duplikate zuverlässig, ohne Fremdpaare zu fluten (Smoke #2) — **Nutzer-Check
      am realen Set, nicht Teil dieser Umsetzung** (private Profil: kein Live-Test/Server-Hochfahren).
- [x] Anzeige (`api/duplicates.py`, `api/review.py`) zeigt korrekte Distanzen/Prozente für das DINOv2-Signal.
- [x] `ruff check .` grün; Tests grün (7 neue Tests + volle Suite ohne neue Failures).

## Doc-Updates
- [x] `docs/decisions/024-two-stage-rerank.md` — Abschnitt „Duplikat-Scan auf DINOv2" mit End-Schwellwert + Begründung.
- [x] `docs/models.md` / `docs/code-map.md` — Dupe-Scan-Signalquelle aktualisiert (SigLIP2 → DINOv2).
- [x] STATE.md auf `(kein aktiver Plan)` bzw. nächsten Plan zeigen lassen; P37 nach `docs/archive/2026-07/` verschoben.

## Report-Back

**Umgestellt auf DINOv2** (ADR-024, alle vier Stellen, die zuvor `clip_embedding` für Duplikat-/
Near-Dupe-Vergleiche lasen):
1. `embedding_job._check_for_dupes` (Post-Embedding-Check beim Import) — läuft nur bei aktivem
   DINOv2-Modell, kein SigLIP2-Fallback (Duplikat-Erkennung = Primärsignal, kein Rerank).
2. `dupe_scan_job.run_dupe_scan_job` („Duplikate scannen", voll + Selektion).
3. `api/duplicates.py::search_person_duplicates` (Personen-Duplikatsuche).
4. `collections/stats.py` + `api/collections.py::list_collection_duplicates` (Trainings-Set-Near-Dupe,
   eigene Entscheidung in Phase 4 — gleiche Fragestellung, gleiche Begründung).

**Bewusst nicht umgestellt:** `GET /assets/{id}/similar` (Lightbox/MCP „ähnliche Bilder") — andere
Fragestellung, eigener Schwellwert, kein Duplikat-Feature.

**Neue Settings-Keys + Default-Begründung:**
- `dupe_dino_threshold` = **0.08** (≈ 92 % Cosine-Ähnlichkeit).
- `training_near_dupe_dino_threshold` = **0.12** (≈ 88 %, bewusst lockerer als der strenge Dupe-Wert,
  gleiches Verhältnis wie zuvor bei CLIP 0.03/0.05).
- Beides sind **begründete Startwerte, keine empirisch kalibrierten** — DINOv2s Distanz-Regime
  unterscheidet sich von CLIP/SigLIP2, eine Eins-zu-eins-Übernahme des alten Werts wäre falsch
  gewesen. Feinjustierung an einem realen Set ist Nutzer-Aufgabe (Smoke-Checkliste #2 im Plan-README) —
  über die Einstellungen-UI justierbar (Bereich 60–99 % Ähnlichkeit, weiter gefasst als der alte
  90–99 %-CLIP-Slider, um Kalibrierungsspielraum zu lassen).
- Alte Keys (`dupe_clip_threshold`, `training_near_dupe_clip_threshold`) bleiben inert für Rollback.

**Nebenbei gefunden und mitgefixt:** `dupe-check-dialog.ts` reichte bei der Personen-Duplikatsuche
den alten CLIP-Schwellwert an den jetzt-DINOv2-Endpunkt weiter — hätte den neuen Default verdeckt.

**Tests:** neue Datei `backend/tests/test_dupe_scan_dino.py` (7 Tests) — deckt alle vier Umstellungen
inkl. „CLIP sagt nah, DINOv2 sagt fern (und umgekehrt)"-Fällen, die eine versehentlich stehen
gebliebene CLIP-Lesestelle sofort auffliegen lassen würden. Volle Backend-Suite: 213 grün, 13 vorbestehende
Fehler in `test_comfyui_run.py`/`test_comfyui_auto_import.py`/`test_caption_config.py` — unabhängig von
dieser Phase (Signatur-Drift bei `run_comfyui_run_job`), nicht angefasst.

🟡 **Bekannter Trade-off:** Ohne aktives DINOv2-Modell läuft ab jetzt **kein** automatischer
Duplikat-Check mehr beim Import (vorher lief er immer, da SigLIP2 praktisch immer aktiv ist). Wer
DINOv2 nicht über die Modelle-UI lädt, verliert die Auto-Erkennung — bewusste Konsequenz aus
ADR-024, kein Bug.
