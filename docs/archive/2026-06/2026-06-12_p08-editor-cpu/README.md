# P8 — Editor CPU (Stage 4)

> Status: complete · Quelle: [Konzept](../../Konzept-Photofant.md) §8 · Abhängigkeiten: P2, P4 (rembg); Smart-Crop voll erst mit P7. **Vorziehbar vor P7**, wenn gewünscht.

Vollständiger lokaler Editor für nicht-generative Operationen: Crop/Rotate/Mirror/Convert/Pad, rembg, Versionierung mit bewusstem Speichern und flüchtiger Step-History in der Cache-DB. Edits wirken auf Fotos, Face-Crops **und** bestehende Edits (Versionskette).

## Overview

| Phase | Topic | Rating | Status |
|---|---|---|---|
| 1 | [Editor-Shell & Step-History](phase-1-editor-shell-history.md) | heikel | complete |
| 2 | [Geometrie-Operationen](phase-2-geometrie-ops.md) | heikel | complete |
| 3 | [rembg & Smart-Crop](phase-3-rembg-smartcrop.md) | standard | complete |
| 4 | [Versionierung & Speichern](phase-4-versionierung.md) | heikel | complete |
| 5 | [Neuverarbeitung, Vergleich & Bulk](phase-5-neuverarbeitung-bulk.md) | standard | complete |

## Kontrakt (Backend ↔ Frontend)

- **Edit-Session:** `POST /api/edit-sessions` — `{ target: { kind: "instance" | "face" | "version", id } }` → `{ session_key }`. Steps: **`POST /api/edit-sessions/{key}/steps`** — `{ op, params }` → Backend rechnet, legt `edit_step` (Cache-DB: op, params, preview) an, Response `{ seq, preview_url }`. **`POST /api/edit-sessions/{key}/rollback`** — `{ to_seq }`.
- **Speichern:** `POST /api/edit-sessions/{key}/save` — `{ mode: "overwrite" | "new_copy" }` → rendert final, schreibt nach `personX/edits/`, legt `version` an (parent_id-Kette, `is_current`), Response VersionDto. Session ohne Save = nichts im Dateisystem (§8.2).
- **`VersionDto`:** `{ id, type, parent_id, path, is_current, params, created_at, res }`; Detail-Panel-Sektion `versions` + **`POST /api/assets/{id}/set-current`** (`{ version_id }` — Zeiger-Wechsel).
- **Ops Stage 4:** `crop` (frei/Ratio), `smart_crop`, `pad`, `rotate`, `mirror`, `convert` (PNG↔JPEG + Quality), `rembg`.
- **`POST /api/assets/bulk-edit`** — `{ asset_ids, op, params, save_mode }` → Queue-Job (ohne Session, direkter Versions-Write pro Asset).
- **Re-Import:** Import erkennt per Hash-Verwandtschaft nichts automatisch — explizite UI-Aktion „als Version zu X importieren" → `POST /api/assets/{id}/versions/import`.

## Finale Akzeptanzkriterien

1. Editor öffnet Foto/Face/Edit im Full-Viewport (eigene View ohne App-Shell), Tools nach Prototyp; jede Operation erzeugt einen Step mit Vorschau; Rollback auf beliebigen Step — auch nach Backend-Neustart (History lebt in der Cache-DB).
2. Ohne aktives Speichern entsteht **keine** Datei in `personX/edits/`; Speichern (überschreiben/neue Kopie) erzeugt die Version korrekt verkettet; Original bleibt unveränderlich.
3. „Aktuelle Version" wechselbar (Galerie/Lightbox zeigen die aktuelle); ältere Versionen bleiben erhalten; Side-by-side-Vergleich Original vs. Version.
4. Crop-Sonderfall (§8.2a): fällt eine Person raus, wird der Edit nur den verbleibenden Personen zugeordnet; das Original bleibt bei der weggeschnittenen Person.
5. Edits erben Tags/Caption vom Eltern-Asset (keine Re-Klassifizierung); neue Versionen durchlaufen den pHash-Face-Dedupe (§8.3).
6. Bulk: Konvertierung/Rotate/rembg über eine Auswahl läuft als Job mit Fortschritt.

## Smoke-Checkliste (User, am Plan-Ende)

- [ ] Foto croppen → drehen → Rollback auf Schritt 1 → speichern als Kopie → Edit liegt in `edits/`, Original unverändert
- [ ] Editor schließen ohne Speichern → keine neue Datei, History beim Wiederöffnen noch da
- [ ] Version als „aktuell" setzen → Grid/Lightbox zeigen sie; zurückwechseln geht
- [ ] Gruppenbild so croppen, dass Person B rausfällt → Edit nur bei Person A, Original bei B unangetastet
- [ ] Bulk-Konvertierung PNG→JPEG über 20 Bilder → Job läuft durch, Versionen da
- [ ] Face-Crop bearbeiten (z.B. rotate) → Version hängt am Face

## Summary

Vollständiger lokaler Editor implementiert: 5 Phasen, alle Ops (Crop, Pad, Rotate, Mirror, Convert, rembg, Smart-Crop), Step-History mit Rollback in Cache-DB, Versionierung mit Overwrite/New-Copy, pHash-Face-Dedupe nach §8.3, Bulk-Edit-Job + Dialog, Side-by-side-Vergleich.

## Files touched

**Backend**: `jobs/queue.py`, `jobs/bulk_edit_job.py` (neu), `jobs/face_job.py`, `api/assets.py`, `api/edit_sessions.py`, `api/faces.py`, `media/ops.py`, `db/models.py`, `main.py`, Alembic-Migrations.

**Frontend**: `features/editor/*`, `features/galerie/*`, `ui/bulk-bar/*`, `ui/bulk-edit-dialog/*` (neu), `ui/step-bar/*`, `ui/save-modal/*`, `ui/basis-panel/*`, `ui/zoom-stage/*`, `store/editor/*`, `services/asset.service.ts`, `models/*`.

**Docs**: `docs/routes.md`, `docs/planning/…` alle Phase-Dateien.

## Commits

- `15b3cc7` feat(p8): Phase 1 — Editor-Shell & Step-History
- `43f2287` docs(p8): Phase 1 complete — routes.md, Phase-Report, STATE auf Phase 2
- `a3b0ba6` feat(p8): Phase 2 — Geometrie-Operationen (Crop, Pad, Rotate, Mirror, Convert)
- `f1d0735` feat(p8): Phase 3 — rembg & Smart-Crop
- `92ba750` feat(p8): Phase 4 — Versionierung & Speichern
- Phase 5: wird in diesem Commit abgeschlossen

## Deviations from plan

- `save_mode` aus `BulkEditRequest` entfernt — Bulk-Edit erzeugt immer `new_copy` (Overwrite semantisch sinnlos bei unabhängigen Assets in einer Auswahl).
- Side-by-side als zwei `<img>`-Panes statt Slider — einfacher, kein Drag-Overhead, erfüllt AK.
- Vererbungs-Logik ist No-Code: Tags/Caption erben via `parent_id`, Auflösung schreibt `_build_version_params` — nichts zu tun.

## Follow-ups

- P9: `is_upscale_source`-Flag aktivieren + Upscale-Op (Konzept §8.3 Ausnahme).
- Crop-Personen-Replikation (§8.2a): automatisches Anlegen der Version bei allen im Bild verbliebenen Personen — Erweiterungspunkt in `_resolve_save_context` vorbereitet.
