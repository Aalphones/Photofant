# P33 — pHash-Ablösung: Duplikaterkennung komplett auf CLIP/Embeddings

**Ziel:** pHash (DHash) vollständig entfernen. Die vier Funktionen, die er heute trägt,
werden durch CLIP-Embeddings bzw. Face-Embeddings ersetzt — treffsicherer und ohne
zweiten, schwächeren Vergleichsweg. Supersedes ADR-006, baut auf ADR-007 auf.

## Overview

| Phase | Thema | Komplexität | Status |
|---|---|---|---|
| 1 | Dupe-Pipeline Backend (Embedding-Hook, Scan, APIs) | standard | complete |
| 2 | Trainingssets + Face-Dedupe Backend | standard | complete |
| 3 | Frontend-Anpassung | mechanisch | pending |
| 4 | Ausbau: DB-Migration, Modul-Löschung, Docs, ADR-018 | mechanisch | pending |

**Reihenfolge ist hart:** Phase 4 (Spalten-Drop) erst nach 1–3 — vorher liest laufender Code die Spalten noch.

## Chesterton's Fence — was pHash heute tut (verstanden, Ersatz benannt)

| # | Funktion | Wo | Ersatz |
|---|---|---|---|
| 1 | Sofort-Dupe-Check beim Import (find_similar gegen ganze Bibliothek) | `jobs/import_job.py`, `comfyui/importer.py`, `jobs/rerun_job.py` | Dupe-Check **nach dem Embedding-Job** via sqlite-vec-Suche (Phase 1). Hinweis kommt Sekunden später statt sofort — akzeptiert. Byte-identische Kopien fängt weiterhin der Content-Hash (unabhängig von diesem Plan). |
| 2 | Zweite Stimme im Dupe-Scan + Review-UI (UNION mit CLIP, `triggered_by`) | `jobs/dupe_scan_job.py`, `api/duplicates.py`, `api/review.py` | Entfällt ersatzlos — CLIP ist bereits die stärkere Stimme (ADR-007); pHash lieferte in der Praxis schlechte Treffer (Anlass dieses Plans). |
| 3 | Trainingsset-Dupes + Near-Dupe-Quote (pHash-only, kein CLIP-Pfad) | `api/collections.py` `/duplicates`, `collections/stats.py` | CLIP-Pairwise über die Collection-Assets (Embeddings existieren zu dem Zeitpunkt immer; Muster: `_compare_chunk_clip`). |
| 4 | Face-Crop-Dedupe bei Edit-Versionen (quasi-identische Gesichter überspringen) | `api/edit_sessions.py` | Cosine auf **buffalo_l-Face-Embeddings** — liegt an der Stelle bereits vor, fachlich der richtige Vergleich. |

## Kontrakt (API-/Settings-Änderungen — Drift-Anker für alle Phasen)

**DTOs (Backend `api/duplicates.py` + `api/review.py` → Frontend `review.model.ts`, `person.model.ts`):**
- `DupePairDto`: `phash_distance`, `phash_similarity_pct`, `triggered_by` **entfernt**; `clip_distance: float` und `clip_similarity_pct: int` werden **non-null**; `similarity_pct = clip_similarity_pct`.
- `SimilarAssetDto`: `phash_distance` entfernt.
- `POST /api/duplicates/search` Body: `threshold` (Hamming) **entfernt**, `clip_threshold: float` bleibt.
- `CollectionDupePairDto` (`api/collections.py`): `phash_distance: int` → `clip_distance: float`; `similarity_pct = round((1 - clip_distance) * 100)`; Query-Param `threshold` wechselt von Hamming (0–64) auf CLIP-Distanz (float 0..1).
- `ClassifyStep` (`api/classify.py`): Literal-Wert `"phash"` entfernt (Rerun von Embedding triggert den Dupe-Check künftig mit).

**Settings-Keys (`settings.py` — Bestandteil der Plan-Freigabe):**
- **Entfernt:** `dupe_threshold` (seit ADR-007 deprecated), `dupe_phash_enabled`.
- **Bleibt:** `dupe_clip_enabled` (fortan Master-Toggle der Dupe-Erkennung), `dupe_clip_threshold` (0.03), `similar_clip_threshold`.
- **Neu:** `dupe_search_limit` (int, Default 20 — max. Kandidaten pro Asset beim Post-Embedding-Check), `training_near_dupe_clip_threshold` (float, Default 0.05 — Trainingsset-Quote/-Dupes), `face_dedupe_similarity_threshold` (float, Default 0.9 — Face-Crop-Dedupe, similarity ≥ Schwelle ⇒ skip).
- Loader ist verifiziert tolerant: alte Keys in bestehender `settings.json` stören nicht (Deep-Merge über Defaults).

**DB (Phase 4):** Spalten `asset.phash`, `face.phash`, `review_item.phash_distance` fallen weg. Vor dem Drop: unresolved `dupe_candidate`-Items mit `clip_distance IS NULL` löschen (reine pHash-Funde; echte Dupes findet der CLIP-Pfad neu). **Resolved** Items bleiben — sie unterdrücken über den Unique-Index `uq_review_item_pair` die Wiedervorlage entschiedener Paare.

## Risiken

- 🟡 **CLIP deaktiviert ⇒ gar keine Dupe-Erkennung.** Heute war pHash modellfrei. Akzeptiert — CLIP gehört zum ONNX-Kern der App; ohne CLIP fehlen ohnehin Suche/Klassifizierung.
- 🟡 **Threshold-Übertrag:** `dupe_clip_threshold` 0.03 (97 % Ähnlichkeit) ist jetzt der einzige Import-Detektor. Burst-Serien könnten mehr Kandidaten erzeugen als pHash-exact. Tunable per Settings; Smoke-Punkt 2 prüft es.
- 🟡 **Face-Dedupe-Schwelle 0.9 unverifiziert** — Cosine-Verteilung quasi-identischer Crops nicht gemessen. Tunable; Smoke-Punkt 1 prüft es.

## Finale AK (Gesamtergebnis)

1. Kein Vorkommen von `phash`/`imagehash` mehr in `backend/photofant/` und `frontend/src/` (Ausnahme: Alembic-Historie).
2. Import eines Near-Dupes erzeugt nach Abschluss des Embedding-Jobs einen Dupe-Kandidaten in der Review-Queue.
3. Dupe-Scan, Personen-Dupe-Check, Ähnliche-Bilder, Trainingsset-Dupes und -Quote arbeiten CLIP-only; Face-Dedupe bei Edit-Versionen arbeitet auf Face-Embeddings.
4. DB-Migration angewandt; `imagehash` aus den Dependencies; ADR-018 dokumentiert, ADR-006/007 als superseded markiert; models.md/routes.md/code-map.md synchron.

## Smoke-Checkliste (macht Sascha am Plan-Ende; Wackelstellen zuerst)

1. **🔴 Face-Dedupe-Schwelle:** Edit-Session (nur Crop, Gesicht unverändert) speichern → in Personen/_unknown erscheint **kein** zweiter identischer Face-Crop. Danach eine Version mit stark verändertem Gesicht (Inpaint) → **neuer** Crop erscheint. Falls falsch herum: `face_dedupe_similarity_threshold` justieren.
2. **🔴 Import-Dupe-Check:** Dasselbe Bild in zwei Auflösungen importieren → nach dem Embedding-Job (Job-Dock) erscheint ein Dupe-Kandidat. Danach eine Burst-Serie (ähnliche, aber verschiedene Bilder) importieren → keine Kandidaten-Flut; sonst `dupe_clip_threshold` enger stellen.
3. Trainingsset mit bekannten Near-Dupes öffnen → Dupes-Ansicht zeigt die Paare, Quote in den Stats plausibel.
4. Review → Duplikate: Liste lädt, Ähnlichkeit in %, keine pHash-Spalte/Badge mehr; Personen-Dupe-Check-Dialog funktioniert.
5. Rerun-Dialog: kein „pHash"-Schritt mehr; Rerun „Embedding" auf ein Asset erzeugt keine Fehler.
6. Einstellungen → Verarbeitung: pHash-Toggle und alter Schwellwert weg, CLIP-Schwelle vorhanden.

## Summary

_(beim Archivieren füllen)_

## Files touched

_(beim Archivieren füllen)_

## Commits

_(beim Archivieren füllen)_

## Deviations from plan

_(beim Archivieren füllen)_

## Follow-ups

_(beim Archivieren füllen)_
