# P8 · Phase 4 — Versionierung & Speichern

> Rating: **heikel** (Versionsketten + Crop-Sonderfall + Personen-Kopien-Logik treffen aufeinander) · Status: complete

## Kontext (vorher lesen)

- [README.md](README.md) — Kontrakt (save, VersionDto, set-current)
- [Konzept](../../Konzept-Photofant.md) §5 (version-Tabelle), **§8.2 + §8.2a komplett**
- Person-Kopien-Logik (P7 Phase 3), Move-Modul

## Akzeptanzkriterien

- Migration: `version`-Tabelle nach Konzept §5 (instance_id XOR face_id, parent_id-Kette, is_current).
- Save rendert final in Originalauflösung → `personX/edits/`; `overwrite` ersetzt die Datei der bestehenden Version, `new_copy` hängt eine neue Version an die Kette; Original unveränderlich.
- Crop-Sonderfall §8.2a: Face-Detection auf dem Ergebnis bestimmt verbleibende Personen → Edit-Kopien nur für diese; Original-Instanzen unangetastet. (Ohne P7: Edit gehört schlicht zur Person der bearbeiteten Instanz — Sonderfall aktiviert sich mit P7, als FINDINGS-Notiz festhalten.)
- `set-current` wechselt nur den Zeiger; Galerie/Lightbox/Thumbnails folgen der aktuellen Version (Thumbnail für Versionen: `target_kind = edit`).
- Versionen-Timeline im Detail-Panel nach Prototyp (Thumbs, aktiv-Markierung, set-current, Side-by-side-Einstieg).
- Edits von Faces hängen über `version.face_id` (Editor-Target `face`).

## Checkliste

- [x] Migration + Save-Endpoint (Render, Datei-Ablage, Ketten-Logik)
- [x] Crop-Personen-Abgleich (P7-abhängiger Teil sauber gekapselt) → siehe FINDINGS
- [x] set-current + Auslieferungs-Logik (aktuelle Version überall)
- [x] Versionen-Sektion im Detail-Panel (Backend: `versions` in `AssetDetailDto`) — Side-by-side-View ist Frontend (Phase 5)
- [x] Re-Import-Endpoint („als Version zu X")
- [x] Tests: XOR-Constraint in Migration als CHECK, Ketten-Integrität via parent_id FK — private-Profil: keine Unit-Tests
- [x] Doc-Update: docs/models.md (version), routes.md

## Report-Back

- Migration 0018: `version` Tabelle mit XOR-Constraint, Indexe auf `instance_id` / `face_id`
- `POST /api/edit-sessions/{key}/save` — Final-Render in Originalauflösung, Datei in `personX/edits/`, Version-Row mit overwrite/new_copy-Logik
- `POST /api/assets/{id}/set-current` — Zeiger-Wechsel, unset auf Geschwister-Versionen
- `POST /api/assets/{id}/versions/import` — Re-Import als Version (multipart upload)
- `GET /api/versions/{id}/thumbnail` + `/file` — Thumbnail aus Cache-DB, Datei direkt
- `AssetDetailDto.versions[]` mit `VersionDto` (id, type, parent_id, is_current, res, thumbnail_url)
- `version_count` in `AssetDto` jetzt live aus DB (batch-query in list_assets)
- `target.kind = "version"` in Editor-Sessions unterstützt (Edit eines Edits)
- Crop-Sonderfall §8.2a natürlich gekapselt: Version hängt an der editierten Instanz, keine Replikation (FINDINGS-Notiz für Phase 5)
