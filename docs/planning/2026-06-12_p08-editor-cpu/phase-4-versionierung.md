# P8 · Phase 4 — Versionierung & Speichern

> Rating: **heikel** (Versionsketten + Crop-Sonderfall + Personen-Kopien-Logik treffen aufeinander) · Status: pending

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

- [ ] Migration + Save-Endpoint (Render, Datei-Ablage, Ketten-Logik)
- [ ] Crop-Personen-Abgleich (P7-abhängiger Teil sauber gekapselt)
- [ ] set-current + Auslieferungs-Logik (aktuelle Version überall)
- [ ] Versionen-Sektion im Detail-Panel + Side-by-side-View
- [ ] Re-Import-Endpoint („als Version zu X")
- [ ] Tests: Ketten-Integrität (Edit eines Edits), overwrite vs. new_copy, XOR-Constraint
- [ ] Doc-Update: docs/models.md (version), routes.md

## Report-Back
