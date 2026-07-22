# Gesichter-Bereinigung — Ausreißer pro Person finden & löschen

> Ziel: Pro Person die Faces finden, die nicht dazugehören (falsch geclustert) oder technisch
> unbrauchbar sind (schlechte Auflösung, Upscale, unsichere Erkennung), damit sie gezielt
> gelöscht werden können. Architektur-Entscheidung + Score-Formel: [ADR-033](../../decisions/033-face-cleanup-score-on-demand.md).

## Overview

| Phase | Thema | Rating | Status |
|---|---|---|---|
| 1 | Backend-Scoring-Modul + Settings | standard | complete |
| 2 | Backend-API (DTO-Erweiterung + Bulk-Delete) | standard | complete |
| 3 | Frontend-Model + Service | mechanisch | complete |
| 4 | Frontend-UI (Cleanup-Dialog + Verdrahtung) | standard | complete |

## Kontrakt (Backend ↔ Frontend)

**`GET /api/persons/{person_id}/faces`** (bestehender Endpoint, additiv erweitert — Sortierung
bleibt `Face.id.asc()`, unverändert für den bestehenden `split-dialog`):

```jsonc
// PersonFaceDto — neue Felder ans Ende, alle mit Default, nichts Bestehendes bricht
{
  "id": 123,
  "asset_id": 45,
  "crop_url": "/faces/123/thumbnail",
  "score": 0.91,          // buffalo_l Detection-Score (bestehend)
  "age": 34,              // (bestehend)
  "resolution": 15625,    // NEU — Crop-Pixel (height*width), aus Face.resolution
  "is_upscaled": false,   // NEU — aus Face.is_upscaled
  "identity_distance": 0.62, // NEU — Cosine-Distanz zum Personen-Centroid; null = nicht berechenbar
  "cleanup_score": 0.71,  // NEU — 0..1, höher = eher Löschkandidat; 0 = kein Problem erkannt
  "cleanup_reasons": ["identity_mismatch", "low_resolution"] // NEU — Teilmenge von vier festen Strings
}
```

`cleanup_reasons` ist eine Teilmenge von genau vier Werten (siehe [ADR-033](../../decisions/033-face-cleanup-score-on-demand.md)):
`identity_mismatch` · `low_resolution` · `low_detection_score` · `upscaled`.

**`POST /api/faces/bulk-delete`** (neu):

```jsonc
// Request
{ "face_ids": [123, 456] }

// Response
{ "deleted": 2, "asset_ids": [45, 78] }
```

Verhalten pro Face identisch zum bestehenden `DELETE /faces/{id}` (Crop-Datei weg, Vektor-Index
weg, verwaiste Asset-Instanzen aufgeräumt), aber Smart-Album-Reevaluation + Empfehlungs-Invalidierung
laufen **einmal pro betroffenem Asset** statt einmal pro Face (vermeidet N Mini-Jobs im Job-Dock,
wenn der Nutzer 15 Faces auf einmal löscht).

## Finale Abnahmekriterien (Gesamt-Feature)

- Im Personen-Menü einer benannten Person gibt es „Gesichter bereinigen…" (Icon `trash`),
  öffnet einen neuen Dialog analog `split-dialog`.
- Der Dialog zeigt alle Faces der Person, sortiert nach `cleanup_score` absteigend (höchster
  Verdacht zuerst), jedes mit Score-Badge + Grund-Chips (bei `cleanup_score > 0`).
- Mehrfachauswahl per Klick (wie `split-dialog`), „Ausgewählte löschen" fragt einmal nach
  Bestätigung, ruft dann `POST /api/faces/bulk-delete` und entfernt die gelöschten Faces aus
  der lokalen Liste — Dialog bleibt offen für weitere Auswahl/Löschung.
- Es lässt sich nie die **letzte verbleibende** Face-Auswahl der Person löschen (Analog zu
  `canSplit()` in `split-dialog.ts` — eine Person ganz leer räumen ist „Person auflösen",
  ein separater, expliziter Flow).
- Nach Abschluss (Dialog schließen) sind Personen-Fotoanzahl/Portrait im Grid aktuell
  (`personsActions.loadPersons()` wurde getriggert).
- `docs/code-map.md` nennt den neuen Dialog + das neue Scoring-Modul unter „Personen & Faces".

## Design-Treue

Für „Gesichter bereinigen" existiert **kein Mockup** in `docs/design/js/` — wie bei
`split-dialog`/`merge-dialog`/`delete-person-dialog` selbst (die laut
`docs/design-reconciliation.md` als „Personen — sauber-verschoben" ohne eigenes Figma/JSX-Pendant
gebaut wurden). Entscheidung (🔴 an den User gestellt, siehe Übergabe-Notiz): **freihändig, 1:1
im visuellen Muster von `split-dialog`** (Grid aus Face-Kacheln, Score-Badge oben rechts pro
Kachel, Footer mit Zähler + Abbrechen/Bestätigen) — Phase 4 spezifiziert das im Detail, keine
weitere Rückfrage nötig.

## Bewusster Scope-Cut

Die fünf neuen `face_cleanup_*`-Settings (Schwellen/Gewichte) bekommen **keine** Einstellungen-UI
in dieser Phase — Begründung + Präzedenzfall in [ADR-033](../../decisions/033-face-cleanup-score-on-demand.md).
Wird das Scoring in der Praxis zu aggressiv/lasch, ist das ein Kandidat für einen Folge-Plan mit
Slidern (Muster: `face_auto_threshold` in `features/einstellungen/verarbeitung/`).

## Gefundener Nebenbefund (nicht Teil dieses Plans)

Beim Lesen von `ui/icon/icon.ts` fiel auf: die Icons `merge` und `split` haben **denselben**
SVG-Pfad (Zeilen 49/50) — vermutlich ein Copy-Paste-Rest, beide Buttons zeigen aktuell dasselbe
Pfeil-Icon. Kosmetisch, keine Funktionsauswirkung. Nicht in diesem Plan gefixt — separat freigeben,
falls gewünscht.

## Bottom-Sektionen (beim Archivieren füllen)

### Summary
Pro Person lassen sich Ausreißer-Gesichter (falsch geclustert oder technisch unbrauchbar)
finden und gezielt löschen. Backend berechnet einen Score on-demand aus vier Signalen
(Identitäts-Abstand zum Personen-Centroid, Auflösung, Detection-Score, Upscale-Flag,
ADR-033), Frontend zeigt sie im neuen „Gesichter bereinigen…"-Dialog sortiert nach
Verdacht, mit Mehrfachauswahl und Bulk-Delete (ein Job-Dock-Eintrag pro betroffenem Asset
statt einem pro Face).

### Files touched
- Backend: `backend/photofant/clustering/cleanup.py` (neu, Scoring), `settings.py`
  (5 neue `face_cleanup_*`-Schwellen), `api/faces.py` (`POST /faces/bulk-delete`),
  `api/persons.py` (`GET /{id}/faces` um 4 Felder erweitert)
- Frontend: `models/person.model.ts`, `services/person.service.ts`,
  `features/personen/cleanup-dialog/` (neu), `features/personen/person-card/`,
  `features/personen/personen.ts`/`.html`
- Doku: `docs/code-map.md` (Zeile „Personen & Faces")

### Commits
`1c2c477` Phase 1 (Backend-Scoring) · `1eeb66e` Phase 2 (Backend-API) ·
`6ad67d1` Phase 3 (Frontend-Model + Service) · Phase 4 (Frontend-UI) — dieser Commit.

### Deviations from plan
Keine — alle 4 Phasen 1:1 nach Spezifikation umgesetzt.

### Follow-ups
- Manueller Browser-Smoke (Phase 4, kein Mockup vorhanden) steht noch aus — siehe
  Smoke-Checkliste unten.
- Bewusster Scope-Cut aus der Planung bleibt bestehen: keine Einstellungen-UI für die
  fünf `face_cleanup_*`-Schwellen. Wird das Scoring in der Praxis zu aggressiv/lasch,
  Folge-Plan mit Slidern (Muster: `face_auto_threshold`).
- Nebenbefund (nicht gefixt): `merge`/`split`-Icons in `ui/icon/icon.ts` (Zeilen 49/50)
  teilen sich denselben SVG-Pfad — kosmetisch, separat freigeben falls gewünscht.
