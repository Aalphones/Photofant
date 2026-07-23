# Phase 8 — Doku-Konsolidierung (code-map, models, routes)

**Komplexität:** mechanisch (reine Doku-Nacharbeit, keine Code-Änderung).

**Voraussetzung:** Phase 1-7 abgeschlossen. Jede Phase trägt bereits ihre eigene lokale
Doc-Update-Zeile — diese Phase ist die **Konsolidierung**: Cross-Check, dass nichts vergessen
wurde, plus die zwei Tabellen-Zeilen, die mehrere Phasen gemeinsam betreffen.

## Kontext (lesen vor dem Start)

- [docs/code-map.md:30](../../../docs/code-map.md#L30) — Zeile „Personen & Faces" (sehr lange
  Tabellenzeile — nur **anhängen**, nicht umschreiben).
- [docs/code-map.md:51](../../../docs/code-map.md#L51) — Zeile „Trainingssets & Export".
- [docs/routes.md:61-67](../../../docs/routes.md#L61) — bestehende Collection-Item-Routen
  (`POST/DELETE/GET/PATCH .../items...`).
- [docs/routes.md:1004](../../../docs/routes.md#L1004) — `POST /comfyui/defaults/{task}/run`.
- [docs/models.md](../../../docs/models.md) — `collection_item`- und `face`-Tabellenbeschreibung
  (Phase 1/4 haben dort bereits eigene Änderungen vorgenommen — hier nur gegenlesen, nicht
  duplizieren).

## Aufgabe 1 — Cross-Check: alle phasen-lokalen Doc-Updates erledigt?

Gegen jede Phasendatei prüfen, ob ihr „Doc-Updates"-Abschnitt tatsächlich umgesetzt wurde:

- [ ] Phase 1: `docs/models.md` — `collection_item` (`id`-PK, `face_id`, XOR).
- [ ] Phase 2: `docs/routes.md` — neue Face-Item-Routen.
- [ ] Phase 3: `docs/code-map.md` — Trainingssets-Zeile (Stats/Export lesen jetzt Face-Items).
- [ ] Phase 4: `docs/routes.md` (`DefaultRunRequest`), `docs/code-map.md`
      (`photofant/media/versions.py`).
- [ ] Phase 6: `docs/code-map.md` — Personen-&-Faces-Zeile (Mehrfachauswahl-Fähigkeit).
- [ ] Phase 7: `docs/code-map.md` — neue `face-bulk-bar`-Komponente.

Fehlt eine dieser Zeilen (z. B. weil eine Phase von einem anderen Modell/einer anderen Session
umgesetzt wurde, ohne den Doc-Update-Schritt mitzuziehen) — hier nachholen, nicht überspringen.

## Aufgabe 2 — `docs/code-map.md` Zeile 30 („Personen & Faces") ergänzen

Ans Ende der zweiten Spalte (Backend-Spalte, nach `media/person_folders.py (...)`) anhängen:

```
· `db/models.py` (`CollectionItem.face_id`, ADR-035 — Face-Crops als Trainingsset-Mitglieder) ·
`comfyui_run_job.py`/`media/versions.py` (Face-Upscale-Auto-Import, ADR-036, setzt
`Face.is_upscaled`)
```

Ans Ende der ersten Spalte (Frontend-Spalte) anhängen: `· features/galerie/face-bulk-bar/`
(nach dem bestehenden `face-cell/`, `face-grid/`-Eintrag).

## Aufgabe 3 — `docs/code-map.md` Zeile 51 („Trainingssets & Export") ergänzen

Ans Ende der Backend-Spalte anhängen:

```
· Face-Items (ADR-035): `collections/stats.py` zählt sie in `total`/`ar_buckets` (bbox-Maße),
`jobs/export_job.py` schreibt Crop-Bild + Sidecar aus `Face.crop_path`/`caption_override` — beide
ohne eigene Trainingsset-Editor-UI-Anpassung (siehe Plan-Phase-2 „Bewusst außerhalb")
```

## Aufgabe 4 — `docs/routes.md` neue Zeilen (nach Zeile 67 einfügen)

```
| `/galerie` (Gesichter-Bulk-Bar „Löschen") | `POST` | `/api/faces/bulk-delete` | `{ face_ids: number[] }` | bereits vorhanden (P-Personen), jetzt zusätzlich aus der Galerie erreichbar |
| `/galerie` (Gesichter-Bulk-Bar „Zu Trainingsset") | `POST` | `/api/collections/{id}/items` | `{ asset_ids: number[], face_ids: number[] }` | `204` — face_ids seit ADR-035, Crop wird eigenständiges Mitglied |
| `/trainingssets` (Item-Grid, Face-Items) | `GET` | `/api/collections/{id}/items` | — | `TrainingSetItemDto[]` — Face-Items mit `kind="face"`, `thumbnail_url` gesetzt, `tags=[]` |
| — | `DELETE` | `/api/collections/{id}/items/faces/{face_id}` | — | `204` — Geschwister-Route zu `.../items/{asset_id}`, seit ADR-035 |
| — | `PATCH` | `/api/collections/{id}/items/faces/{face_id}` | `{ caption_override: string \| null }` | `204` — Face-Items haben keine Original-Caption, override ist einzige Quelle |
| `/galerie` (Gesichter-Bulk-Bar „Hochskalieren") | `POST` | `/api/comfyui/defaults/upscale/run` | `DefaultRunRequest` mit `target_face_ids` + `face_inputs` statt `target_asset_ids`/`inputs` | `{ jobs: [{ job_id }] }` — Ergebnis wird als face-gebundene Version importiert, ADR-036 |
```

## Aufgabe 5 — ADR-Querverweise gegenlesen

- [ ] `docs/decisions/035-collection-item-face-support.md` verlinkt korrekt auf `033`
      (Face.is_upscaled/Cleanup-Score-Kontext) — Platzhalter-Link `[018](018-...)` aus der
      Phase-1-Vorlage durch den tatsächlichen Dateinamen ersetzen (`Version`-Modell hat evtl.
      kein eigenes ADR — falls nicht vorhanden, den Verweis auf die Modell-Zeile in `models.py`
      umstellen statt eine nicht existierende Datei zu verlinken).
- [ ] `docs/decisions/036-face-upscale-auto-import.md` verlinkt korrekt auf `013`
      (Asset-Auto-Import) — Dateinamen vor dem Verlinken mit `ls docs/decisions/013*` verifizieren.

## AK dieser Phase

- [ ] Alle sechs Cross-Check-Punkte aus Aufgabe 1 sind erledigt (nicht nur geplant).
- [ ] `docs/code-map.md`, `docs/routes.md` beschreiben den Endzustand aller 7 Code-Phasen korrekt
      — stichprobenartig: ein Entwickler, der nur `code-map.md` liest, findet
      `face-bulk-bar`/`media/versions.py` ohne den Code selbst zu durchsuchen.
- [ ] ADR-Querverweise sind reale, existierende Dateien (kein toter Link).

## Report-Back

_(nach Umsetzung ausfüllen: welche Doc-Zeile in der Praxis am meisten Nacharbeit brauchte)_
