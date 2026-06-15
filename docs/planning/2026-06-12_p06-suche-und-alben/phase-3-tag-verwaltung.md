# P6 · Phase 3 — Tag-Verwaltung & manuelle Korrektur

> Rating: standard · Status: pending

## Kontext (vorher lesen)

- [README.md](README.md) — Kontrakt (tags-Endpoints, Korrektur-Trigger)
- [Konzept](../../Konzept-Photofant.md) §10 (Tags & Captions manuell korrigierbar, Tag-Verwaltung)

## Akzeptanzkriterien

- Detail-Panel: Tag hinzufügen (Autocomplete, neue Tags `kind = manual` mit Dot-Indikator nach Prototyp), Tag entfernen, Caption editieren (Inline-Textarea).
- Manuelle Korrekturen als bevorzugt markiert: Rerun überschreibt manuell entfernte Auto-Tags nicht wieder und lässt manuelle Tags/editierte Captions stehen (Entfernen-Liste bzw. Edit-Flag in der DB).
- Tag-Verwaltungs-View: Liste mit Counts, Umbenennen, Merge (alias_of — Suche/Filter lösen Aliase auf), Bulk-Tagging über die Bulk-Bar.
- `tags`-Slice.

## Checkliste

- [ ] DB-Erweiterung: Mechanik für „manuell entfernt"/„manuell editiert" (kleine Migration; Konzept lässt die Form offen → Findung dokumentieren)
- [ ] Endpoints (assets/tags, assets/caption, tags CRUD/merge/bulk) inkl. Alias-Auflösung in Filter/Suche
- [ ] Detail-Panel-Editierbarkeit (Tags, Caption)
- [ ] Tag-Verwaltungs-View + Bulk-Bar-Aktion „Taggen"
- [ ] Neubewertungs-Hook vorbereiten (no-op bis Phase 4, danach echt)
- [ ] Doc-Update: routes.md, docs/models.md

## Report-Back
