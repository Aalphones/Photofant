# P4 · Phase 1 — Registry & Manifest

> Rating: standard · Status: complete

## Kontext (vorher lesen)

- [README.md](README.md) — Kontrakt (Status-Enum, Manifest-Form, Capabilities)
- [Konzept](../../Konzept-Photofant.md) §5 (model_registry, app_config), §12.1, §12.3 (Modell-Tabelle)

## Akzeptanzkriterien

- Migration: `model_registry` nach Konzept §5 (inkl. `components`/`caption_mode`/`capabilities` — Spalten jetzt, Nutzung später).
- Manifest-JSON mit den fünf Core-Modellen (URL, SHA, Größe, Rolle, Format, Lizenz); Manifest-Loader validiert beim Start.
- `GET /api/models` joint Manifest + Registry zu Status (`missing`/`available`/`active`/`inplace`); `GET /api/models/capabilities` leitet Feature-Flags aus aktivierten Rollen ab.
- `models_dir` über `GET/PATCH /api/config`, Default im App-Verzeichnis.

## Checkliste

- [x] Migration + SQLAlchemy-Modelle
- [x] `manifest.json` (Core-Modelle, gepinnte Versionen/Quellen recherchieren und dokumentieren)
- [x] Status-Logik + Endpoints (`/models`, `/models/capabilities`, `/config`)
- [x] Doc-Update: docs/models.md (model_registry), README-Sektion „Modelle" (Quellen + Lizenzen, Konzept-Anforderung §12.1)

## Report-Back

2026-06-17: Phase abgeschlossen. Neu: `backend/alembic/versions/0004_model_registry.py`, `backend/photofant/models/manifest.json`, `backend/photofant/models/loader.py`, `backend/photofant/api/models.py`, `backend/photofant/api/config.py`. SQLAlchemy-Modelle in `db/models.py` ergänzt. Migration 0001→0004 sauber durchgelaufen, alle 20 Tests grün.

Abweichung: `manifest_id`-Spalte in `model_registry` hinzugefügt (Konzept §5 sieht sie nicht vor, ist aber für den Manifest→Registry-Join nötig). FINDINGS.md trägt 2 Phase-2-Aufgaben: SHA-256-Hashes befüllen, Florence-2 HF-Repo-Download behandeln.
