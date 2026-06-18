# STATE

**Aktiver Plan:** `docs/planning/2026-06-18_settings-json-infrastruktur/`
**Phase:** 2/2 — Migration: app_config → settings.json, app_config Drop (pending)
**Nächster Schritt:** Phase 2 starten — tagging_job/heuristics_job/import_job auf load_settings() umstellen, ReconcileReport-Tabelle anlegen, Alembic Data-Migration + DROP TABLE app_config. Phase ist "heikel" → `/model opusplan` empfohlen.

**Backlog-Pläne (nach Settings-Infra):**
- P7 Personen: `docs/planning/2026-06-12_p07-personen/`
- P8 Editor CPU: `docs/planning/2026-06-12_p08-editor-cpu/`
- P8b ComfyUI: `docs/planning/2026-06-15_p08b-comfyui-integration/`
- P9 Generativ: `docs/planning/2026-06-12_p09-generativ/`
- P10 Trainingssets: `docs/planning/2026-06-12_p10-trainingssets-export/`

**Geparkte Side-Quests (Reihenfolge beachten):**
- **[1] Settings-JSON-Infrastruktur** — Phase 1 complete, Phase 2 aktiv (oben)
- **[2] Einstellungen Thumbnail-Qualität** (benötigt [1]): `docs/planning/2026-06-18_einstellungen-thumbnail-qualitaet/` — 3 Phasen
- **[2] Einstellungen fehlende Sektionen** (benötigt [1]): `docs/planning/2026-06-18_einstellungen-fehlende-sektionen/` — 4 Phasen
