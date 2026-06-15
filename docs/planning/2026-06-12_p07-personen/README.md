# P7 — Personen & Faces (Stage 3)

> Status: geparkt · Quelle: [Konzept](../../Konzept-Photofant.md) §6.1a/b, §7 · Abhängigkeiten: P2, P4 (P5 für Framing-Nachtrag, P6 für Person-Trigger)

Google-Fotos-Kern: Face-Detection und -Recognition, Auto-Clustering in Person-Ordner mit echten Kopien, Review-Queue, Merge/Split, direkter Face-Import. Hier zahlt sich das Move-Modul aus P2 aus — **physische Moves + DB-Konsistenz sind das Kernrisiko dieses Plans.**

## Overview

| Phase | Topic | Rating | Status |
|---|---|---|---|
| 1 | [Face-Engine](phase-1-face-engine.md) | standard | pending |
| 2 | [Clustering & Auto-Zuordnung](phase-2-clustering.md) | heikel | pending |
| 3 | [Person-Ordner & Kopien](phase-3-person-ordner.md) | heikel | pending |
| 4 | [Personen-View](phase-4-personen-view.md) | standard | pending |
| 5 | [Review-Queue, Merge & Split](phase-5-review-merge-split.md) | heikel | pending |
| 6 | [Face-Import, Duplikate & Rebuild](phase-6-face-import-dupes.md) | standard | pending |

## Kontrakt (Backend ↔ Frontend)

- **`GET /api/persons`** → `[{ id, name, is_unknown, count, fav_count, portrait_face_id }]`; **`PATCH /api/persons/{id}`** (rename); **`POST /api/persons/merge`** (`{ from_id, into_id }`); **`POST /api/persons/{id}/split`** (`{ face_ids }` → neue Person).
- **`GET /api/persons/{id}/assets`** — über den bestehenden Assets-Endpoint (`person_id`-Filter).
- **`FaceDto`:** `{ id, asset_id, person_id, crop_url, score, age, bbox, origin, is_upscaled }` — Detail-Panel-Erweiterung `faces: FaceDto[]`.
- **`PATCH /api/faces/{id}/assign`** — `{ person_id }` → physischer Move der Bilddatei + Umhängen (Konzept §7); Response: betroffene Instanzen.
- **`GET /api/faces/{id}/matches`** → Top 10 **disjunkte** Personen `[{ person_id, best_face_id, score }]` (Score 0–1, UI zeigt %).
- **`GET /api/review-queue`** → unsichere Zuordnungen `[{ face_id, suggested_person_id, score, asset_id }]`; **`POST /api/review-queue/{face_id}`** — `{ action: "confirm" | "reject" }`.
- **`POST /api/persons/{id}/import`** — Dateien direkt in einen Person-Ordner (setzt `fixed_person`); **`POST /api/faces/import`** — direkter Face-Import (`origin = manual_original`).
- **`POST /api/duplicates/search`** — `{ person_id, threshold }` → Paare mit Ähnlichkeits-% (pHash-Hamming → %).
- **Schwellen (in `app_config`, Defaults):** Auto-Zuordnung ≥ 0.6 Cosine, Review-Queue 0.45–0.6, darunter `_unknown`. Werte bei Umsetzung am realen Bestand kalibrieren (FINDINGS).

## Finale Akzeptanzkriterien

1. Import eines Bestands mit mehreren Personen → Cluster entstehen, Person-Ordner mit echten Kopien pro erkannter Person, Rest in `_unknown`; Face-Crops (mit Padding) in `personX/faces/`.
2. Bild mit zwei Personen liegt als Kopie in beiden Ordnern; Favorit in Ordner A beeinflusst Ordner B nicht.
3. Falsch zugeordnetes Bild manuell korrigieren → Datei wandert physisch (inkl. Faces/Edits), DB konsistent, Smart-Album der falschen Person verliert das Bild (P6-Hook).
4. Review-Queue: unsichere Matches bestätigen/ablehnen im Google-Fotos-Stil; bestätigt → Move, abgelehnt → `_unknown`.
5. Merge führt zwei Personen zusammen (physisches Verschieben aller Bilder); Split trennt markierte Faces in eine neue Person.
6. Manuell in einen Person-Ordner gelegte Datei wird erkannt, verarbeitet, bleibt fix bei der Person (`fixed_person`); zusätzlich erkannte Personen bekommen Kopien (§6.1a).
7. Direkter Face-Import: Bild ist selbst der Crop, Embedding wird berechnet, voll matchbar (§6.1b); Face-Rebuild überschreibt manuelle Originale nie.
8. Framing-Heuristik (BBox/Bild) trägt die P5-Lücke nach; Personen-Facette, Person-Gruppierung und Person-Trigger (P6) werden aktiv.

## Smoke-Checkliste (User, am Plan-Ende)

- [ ] Bestand mit ≥3 bekannten Personen importieren → Cluster stimmen grob, `_unknown` enthält den Rest
- [ ] Gruppenbild → Kopie in jedem beteiligten Person-Ordner
- [ ] Bewusst falsche Zuordnung produzieren/finden → korrigieren → Datei physisch im richtigen Ordner, Galerie-Filter stimmt
- [ ] Review-Queue abarbeiten (beide Aktionen) → Ergebnis wie beschriftet
- [ ] Zwei doppelte Personen mergen → ein Ordner, eine Person, nichts verloren (Datei-Count vorher/nachher)
- [ ] Foto direkt in einen Person-Ordner kopieren → taucht nach Scan bei dieser Person auf und bleibt dort

## Summary

## Files touched

## Commits

## Deviations from plan

## Follow-ups
