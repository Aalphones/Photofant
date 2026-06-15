# P4 · Phase 1 — Registry & Manifest

> Rating: standard · Status: pending

## Kontext (vorher lesen)

- [README.md](README.md) — Kontrakt (Status-Enum, Manifest-Form, Capabilities)
- [Konzept](../../Konzept-Photofant.md) §5 (model_registry, app_config), §12.1, §12.3 (Modell-Tabelle)

## Akzeptanzkriterien

- Migration: `model_registry` nach Konzept §5 (inkl. `components`/`caption_mode`/`capabilities` — Spalten jetzt, Nutzung später).
- Manifest-JSON mit den fünf Core-Modellen (URL, SHA, Größe, Rolle, Format, Lizenz); Manifest-Loader validiert beim Start.
- `GET /api/models` joint Manifest + Registry zu Status (`missing`/`available`/`active`/`inplace`); `GET /api/models/capabilities` leitet Feature-Flags aus aktivierten Rollen ab.
- `models_dir` über `GET/PATCH /api/config`, Default im App-Verzeichnis.

## Checkliste

- [ ] Migration + SQLAlchemy-Modelle
- [ ] `manifest.json` (Core-Modelle, gepinnte Versionen/Quellen recherchieren und dokumentieren)
- [ ] Status-Logik + Endpoints (`/models`, `/models/capabilities`, `/config`)
- [ ] Doc-Update: docs/models.md (model_registry), README-Sektion „Modelle" (Quellen + Lizenzen, Konzept-Anforderung §12.1)

## Report-Back
