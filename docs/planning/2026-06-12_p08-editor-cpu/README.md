# P8 — Editor CPU (Stage 4)

> Status: geparkt · Quelle: [Konzept](../../Konzept-Photofant.md) §8 · Abhängigkeiten: P2, P4 (rembg); Smart-Crop voll erst mit P7. **Vorziehbar vor P7**, wenn gewünscht.

Vollständiger lokaler Editor für nicht-generative Operationen: Crop/Rotate/Mirror/Convert/Pad, rembg, Versionierung mit bewusstem Speichern und flüchtiger Step-History in der Cache-DB. Edits wirken auf Fotos, Face-Crops **und** bestehende Edits (Versionskette).

## Overview

| Phase | Topic | Rating | Status |
|---|---|---|---|
| 1 | [Editor-Shell & Step-History](phase-1-editor-shell-history.md) | heikel | complete |
| 2 | [Geometrie-Operationen](phase-2-geometrie-ops.md) | heikel | pending |
| 3 | [rembg & Smart-Crop](phase-3-rembg-smartcrop.md) | standard | pending |
| 4 | [Versionierung & Speichern](phase-4-versionierung.md) | heikel | pending |
| 5 | [Neuverarbeitung, Vergleich & Bulk](phase-5-neuverarbeitung-bulk.md) | standard | pending |

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

## Files touched

## Commits

## Deviations from plan

## Follow-ups
