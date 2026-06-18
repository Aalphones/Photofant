# Settings-JSON-Infrastruktur · Phase 2 — Migration: app_config → settings.json, Drop

> Rating: **heikel** · Status: complete · Voraussetzung: Phase 1 abgeschlossen

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

- [x] **`jobs/tagging_job.py`**: `_get_threshold()` durch inline `load_settings()["tagging_threshold"]` ersetzt (SQL + Fallback-Konstanten raus)
- [x] **`jobs/heuristics_job.py`**: `_REFERENCE_SHARPNESS`-Konstante raus → `load_settings()["blur_threshold"]` als Parameter an `_compute_quality`
- [x] **`jobs/import_job.py`**: neuer `_enqueue_pipeline()`-Helper liest `auto_tag`/`auto_caption`/`auto_embed` aus `load_settings()` und gated Tagging/Caption/Embedding (Thumbnails+Heuristiken laufen immer); konsolidiert die zwei identischen Enqueue-Blöcke aus Import + Scan
- [x] Alle anderen Stellen via `grep -r "app_config" backend/photofant` — keine direkten SQL-Zugriffe mehr (verifiziert: 0 Treffer im Source)

### Reconcile-Report umziehen

- [x] **Neue DB-Tabelle** `reconcile_report` — Alembic-Migration:
  ```sql
  CREATE TABLE reconcile_report (
      id      INTEGER PRIMARY KEY CHECK (id = 1),  -- max. 1 Zeile
      payload TEXT NOT NULL,                        -- JSON-Blob
      created_at DATETIME NOT NULL
  );
  ```
- [x] **`maintenance/store.py`** umschreiben: `persist_report()` + `load_report()` nutzen `reconcile_report` (raw SQL wie bisher, konsistent gehalten)
- [x] Kein SQLAlchemy-Model — raw SQL beibehalten (wie zuvor bei `app_config`)

### Alembic Data-Migration

- [x] Neue Revision `0013_drop_app_config_to_settings_json.py`:
  - `upgrade()`: app_config-Rows lesen → bekannte Keys (`data_root`/`models_dir`/`tagging_threshold`) in settings.json mergen (nur fehlende Keys) → `reconcile_report`-Tabelle anlegen → Reconcile-Blob transferieren → `DROP TABLE app_config`
  - `downgrade()`: `CREATE TABLE app_config` + Reconcile-Blob zurückschreiben (Best-Effort; settings.json bleibt unangetastet)
- [x] Migration angewendet + Round-Trip (upgrade→downgrade→upgrade) verifiziert; DB auf rev 0013

### Cleanup

- [x] Kein `AppConfig`-SQLAlchemy-Model vorhanden (grep `AppConfig` → 0 Treffer) — nichts zu entfernen
- [x] `ruff check` + `mypy` sauber auf allen berührten Dateien

## Heikel: Was schiefgehen kann

| Risiko | Gegenmaßnahme |
|---|---|
| `settings.json` nicht schreibbar während Migration | Migration wirft Exception → Alembic-Rollback; User-Hinweis in Fehlermeldung |
| `app_config` enthält unbekannte Keys (aus alten Versionen) | Alle Keys die nicht im Settings-Schema sind, ignorieren (nur bekannte Keys migrieren) |
| Migrate + Drop in einer Transaktion | SQLite erlaubt DDL in Transaktionen; aber: `DROP TABLE` ist autocommit → Data-Migration in eigener Transaktion BEFORE Drop |

## Report-Back

- **Datenlage real:** `app_config` war beim Lauf **leer** (0 Rows), DB stand auf 0012 → Data-Migration ein No-op für die echte DB; trotzdem korrekt für den Allgemeinfall + Round-Trip getestet.
- **Reihenfolge geklärt (war das Heikle):** `ensure_settings_file()` läuft im Server-Lifespan, **nicht** beim `alembic upgrade` — die Migration läuft also vor dem ersten Server-Start sauber, solange keine settings.json existiert. Existiert sie schon mit Default-Keys, greift „nur fehlende Keys mergen" → bestehende settings.json gewinnt (gewollt).
- **Verhaltensänderung (Chesterton's Fence):** `import_job` enqueute Tagging/Caption/Embedding bisher **bedingungslos**. Neu gated über `auto_tag`/`auto_caption`/`auto_embed`. Defaults sind alle `true` → Default-Verhalten unverändert; nur wer ein Flag auf `false` setzt, überspringt den Schritt. Das war als „Vorbereitung Verarbeitungs-Plan" im Plan vorgesehen.
- **Deviation:** Plan nannte `_pipeline_flags()`; implementiert als `_enqueue_pipeline()` — bündelt das Settings-Lesen **und** das bedingte Enqueuen und ersetzt die zwei identischen Blöcke in `run_import_job` + `run_scan_job` (weniger Duplikation).
