# P5 · Phase 2 — WD14-Tagging

> Rating: standard · Status: pending

## Kontext (vorher lesen)

- [README.md](README.md) — Kontrakt (Dto-Erweiterung)
- [Konzept](../../Konzept-Photofant.md) §5 (tag/asset_tag), §6.2 (Matrix)
- Phase 1 (Interfaces)

## Akzeptanzkriterien

- Migration: `tag`, `asset_tag` nach Konzept §5.
- WD14-Tagger (swinv2-v3, ONNX + CSV-Labelmap) liefert Tags über Konfidenz-Schwelle (Default ~0.35, in `app_config`); Rating-Tags der Labelmap werden verworfen (keine NSFW-Klassifizierung — Nicht-Ziel).
- Tagging-Job im Import-Fluss (Ledger `tags_done`); Tags als `kind = auto`, Dedupe über `tag.name`.
- Detail-Panel zeigt Tag-Chips (auto-Styling nach Prototyp); manuelle Bearbeitung kommt in P6.

## Checkliste

- [ ] Migration + Tag-Upsert-Logik (case-normalisiert, underscores → Anzeige mit Leerzeichen wie Booru-üblich)
- [ ] WD14-Implementierung des `Tagger`-Interface (CSV-Parsing, Schwelle, Kategorie-Filter)
- [ ] Job + Ledger-Integration
- [ ] Dto/Endpoint-Erweiterung + Frontend-Tags-Sektion im Detail-Panel
- [ ] Doc-Update: docs/models.md (tag-Tabellen)

## Report-Back
