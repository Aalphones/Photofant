# Settings-JSON-Infrastruktur · Phase 2 — Migration: app_config → settings.json, Drop

> Rating: **heikel** · Status: pending · Voraussetzung: Phase 1 abgeschlossen

## Kontext (vorher lesen)

- [README.md](README.md)
- `backend/photofant/jobs/tagging_job.py` — liest `tagging_threshold` direkt aus `app_config` (muss auf `load_settings()` umgestellt werden)
- `backend/photofant/maintenance/store.py` — `reconcile_report` lebt in `app_config` (bekommt eigene Tabelle)
- Alembic-Migrationen: `backend/alembic/versions/`

## Warum heikel

- `app_config` hat Live-Daten: `models_dir`, `tagging_threshold`, evtl. gesetzter `data_root`-Override — diese Werte dürfen beim Drop nicht verloren gehen
- Der Reconcile-Report-Blob muss in eine neue Tabelle umziehen, bevor `app_config` verschwindet
- Alembic-Migration muss Data-Migration + Schema-Migration korrekt trennen

## Migrations-Strategie

1. Alembic-Migration liest bestehende `app_config`-Werte aus, schreibt sie in `settings.json`, legt neue `reconcile_report`-Tabelle an, droppt `app_config`
2. Migration ist idempotent: wenn `settings.json` schon existiert, wird nur gemergt (bestehende Werte gewinnen)

## Akzeptanzkriterien

- `app_config`-Tabelle existiert nach Migration nicht mehr in der DB.
- Bestehende Werte (insbesondere `models_dir`, `tagging_threshold`) sind in `settings.json` gelandet.
- Reconcile-Report aus alter `app_config` ist in neue `reconcile_report`-Tabelle transferiert.
- Alle Backend-Callers lesen Settings aus `load_settings()`, kein direkter `app_config`-SQL mehr.
- Ruff und mypy laufen sauber durch.

## Checkliste

### Callers auf settings.py umstellen

- [ ] **`jobs/tagging_job.py`**: `_get_threshold()` ersetzt DB-Query durch `load_settings().tagging_threshold`
- [ ] **`jobs/heuristics_job.py`**: `_REFERENCE_SHARPNESS` → `load_settings().blur_threshold` (Vorbereitung für Verarbeitungs-Plan)
- [ ] **`jobs/import_job.py`**: `_pipeline_flags()` liest `auto_tag`/`auto_caption`/`auto_embed` aus `load_settings()` (Vorbereitung für Verarbeitungs-Plan)
- [ ] Alle anderen Stellen via `grep -r "app_config" backend/photofant --include="*.py"` — keine direkten SQL-Zugriffe auf `app_config` mehr nach dieser Phase

### Reconcile-Report umziehen

- [ ] **Neue DB-Tabelle** `reconcile_report` — Alembic-Migration:
  ```sql
  CREATE TABLE reconcile_report (
      id      INTEGER PRIMARY KEY CHECK (id = 1),  -- max. 1 Zeile
      payload TEXT NOT NULL,                        -- JSON-Blob
      created_at DATETIME NOT NULL
  );
  ```
- [ ] **`maintenance/store.py`** umschreiben: `persist_report()` und `load_report()` nutzen neue Tabelle statt `app_config`
- [ ] SQLAlchemy-Model `ReconcileReportRow` hinzufügen (oder raw SQL wie bisher, konsistent halten)

### Alembic Data-Migration

- [ ] Neue Revision `xxxx_drop_app_config_migrate_to_settings_json.py`:
  - `upgrade()`:
    1. Bestehende `app_config`-Rows auslesen (mit `op.get_bind()`)
    2. Werte `models_dir`, `tagging_threshold`, `data_root` (falls vorhanden) in `settings.json` mergen (nur schreiben wenn Key nicht bereits in Datei vorhanden)
    3. `reconcile_report`-Row aus `app_config` in neue `reconcile_report`-Tabelle transferieren
    4. `DROP TABLE app_config`
  - `downgrade()`: `CREATE TABLE app_config ...` + alle Werte zurückschreiben aus settings.json + reconcile_report — sollte funktionieren aber ist optionales Best-Effort
- [ ] Migration in `alembic/versions/` committen

### Cleanup

- [ ] `backend/photofant/db/models.py`: `AppConfig`-SQLAlchemy-Model entfernen (falls vorhanden)
- [ ] `ruff check` + `mypy` sauber

## Heikel: Was schiefgehen kann

| Risiko | Gegenmaßnahme |
|---|---|
| `settings.json` nicht schreibbar während Migration | Migration wirft Exception → Alembic-Rollback; User-Hinweis in Fehlermeldung |
| `app_config` enthält unbekannte Keys (aus alten Versionen) | Alle Keys die nicht im Settings-Schema sind, ignorieren (nur bekannte Keys migrieren) |
| Migrate + Drop in einer Transaktion | SQLite erlaubt DDL in Transaktionen; aber: `DROP TABLE` ist autocommit → Data-Migration in eigener Transaktion BEFORE Drop |

## Report-Back
