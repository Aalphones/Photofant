# P6 · Phase 3 — Tag-Verwaltung & manuelle Korrektur

> Rating: standard · Status: complete

## Kontext (vorher lesen)

- [README.md](README.md) — Kontrakt (tags-Endpoints, Korrektur-Trigger)
- [Konzept](../../Konzept-Photofant.md) §10 (Tags & Captions manuell korrigierbar, Tag-Verwaltung)

## Akzeptanzkriterien

- Detail-Panel: Tag hinzufügen (Autocomplete, neue Tags `kind = manual` mit Dot-Indikator nach Prototyp), Tag entfernen, Caption editieren (Inline-Textarea).
- Manuelle Korrekturen als bevorzugt markiert: Rerun überschreibt manuell entfernte Auto-Tags nicht wieder und lässt manuelle Tags/editierte Captions stehen (Entfernen-Liste bzw. Edit-Flag in der DB).
- Tag-Verwaltungs-View: Liste mit Counts, Umbenennen, Merge (alias_of — Suche/Filter lösen Aliase auf), Bulk-Tagging über die Bulk-Bar.
- `tags`-Slice.

## Checkliste

- [x] DB-Erweiterung: tag.alias_of, asset_tag.manually_removed, asset.caption_edited (Migration 0011)
- [x] Endpoints (assets/tags, assets/caption, tags CRUD/merge/bulk) inkl. Alias-Auflösung in Filter/Suche
- [x] Detail-Panel-Editierbarkeit (Tags, Caption)
- [x] Tag-Verwaltungs-View + Bulk-Bar-Aktion „Taggen"
- [x] Neubewertungs-Hook vorbereiten (no-op bis Phase 4, danach echt)
- [ ] Doc-Update: routes.md, docs/models.md

## Report-Back
