# Settings-JSON-Infrastruktur — Zentraler Konfig-Speicher

> Status: geparkt · **Voraussetzung für alle anderen Settings-Pläne** · Muss zuerst umgesetzt werden
> Abhängige Pläne: `2026-06-18_einstellungen-thumbnail-qualitaet`, `2026-06-18_einstellungen-fehlende-sektionen`

Ersetzt die `app_config`-Tabelle und alle Env-Vars durch eine einzelne `settings.json`-Datei. Einzige Konfig-Quelle für alle User-Settings. Editierbar per Texteditor oder über die UI.

## Entscheidungen (fixiert)

| Frage | Entscheidung |
|---|---|
| Datei-Location | `.photofant/settings.json` relativ zum Backend-CWD (= `backend/`) |
| app_config | Komplett abschaffen — alle Keys migrieren |
| Reconcile-Report (war in app_config) | Eigene DB-Tabelle `reconcile_report` (kein User-Setting) |
| Env-Vars | Werden ersetzt — `PHOTOFANT_DATA_ROOT` etc. entfallen; einziger Escape-Hatch für CI/Docker: `PHOTOFANT_SETTINGS_PATH` zum Überschreiben des settings.json-Pfads |
| Commits | `settings.json` in `.gitignore`; `settings.example.json` wird committed |
| Typen | Echte JSON-Typen (`bool`, `number`, `string|null`) statt String-encoded wie in app_config |

## Datei-Location im Detail

```
backend/                      ← CWD beim `uv run uvicorn ...`
└── .photofant/
    ├── settings.json         ← User-Einstellungen (gitignored)
    ├── db.sqlite             ← Datenbank
    └── thumbnails.sqlite     ← Thumbnail-Cache
```

`data_root` IN der settings.json zeigt auf den Wurzelpfad der Medienbibliothek (kann abweichen vom `.photofant/`-Ordner). Default: `null` → App legt Medien in `../Data/` relativ zur `settings.json` ab.

Bootstrap-Reihenfolge:
1. `PHOTOFANT_SETTINGS_PATH` env (nur für CI/Docker-Overrides)
2. `.photofant/settings.json` (relativ zum CWD des Backends)
3. Wenn nicht vorhanden: Datei mit Defaults anlegen

## Overview

| Phase | Topic | Rating | Status |
|---|---|---|---|
| 1 | [Schema + Infrastruktur (Reader, Writer, Defaults)](phase-1-schema-infrastruktur.md) | standard | complete |
| 2 | [Migration: app_config → settings.json, app_config Drop](phase-2-migration.md) | heikel | pending |

## settings.json Schema

```json
{
  "_schema_version": 1,
  "data_root": null,
  "models_dir": null,
  "thumbnail_quality": "md",
  "auto_tag": true,
  "auto_caption": true,
  "auto_embed": true,
  "tagging_threshold": 0.35,
  "blur_threshold": 200.0,
  "trash_auto_days": 30,
  "keyboard_shortcuts": null,
  "display": {
    "locale": "de",
    "date_format": "dmy"
  }
}
```

`null`-Werte = Default gilt. Fehlende Keys = Default gilt (vorwärtskompatibel: neue Settings können hinzukommen ohne dass ältere settings.json Dateien ungültig werden).

## API-Kontrakt (unverändert für Frontend)

`GET /api/config` und `PATCH /api/config` behalten ihre Signatur. Intern lesen/schreiben sie `settings.json` statt der DB. Frontend-Seite muss nichts ändern.

## Finale Akzeptanzkriterien

1. Backend startet ohne Env-Vars; `settings.json` wird bei erstem Start mit Defaults angelegt.
2. `PATCH /api/config` schreibt atomar in `settings.json` (temp-file + rename).
3. `GET /api/config` liefert alle Settings aus `settings.json` mit Defaults für fehlende Keys.
4. `app_config`-Tabelle existiert nicht mehr (Alembic-Migration droppt sie).
5. Reconcile-Report lebt in neuer `reconcile_report`-DB-Tabelle.
6. `settings.json` ist in `.gitignore`; `settings.example.json` ist committed und aktuell.

## Smoke-Checkliste

- [ ] Backend kalt starten (keine `.photofant/` Ordner) → `.photofant/settings.json` wird angelegt mit allen Defaults
- [ ] `cat .photofant/settings.json` → valides JSON, alle Keys vorhanden
- [ ] `PATCH /api/config` mit `{ data: { thumbnail_quality: "lg" } }` → Datei aktualisiert (manuell prüfen), `GET /api/config` liefert `"lg"` zurück
- [ ] `settings.json` löschen → Backend neu starten → Defaults wiederhergestellt (keine Exception)
- [ ] `settings.json` manuell im Texteditor editieren (z.B. `auto_tag: false`) → Backend neu starten → `GET /api/config` liefert `false`
- [ ] `git status` → `settings.json` nicht als untracked gelistet; `settings.example.json` vorhanden

## Summary

## Files touched

## Commits

## Deviations from plan

## Follow-ups

- `PHOTOFANT_SETTINGS_PATH` Env-Var kann später durch einen Settings-Path-Parameter im Startup-Command ersetzt werden (CLI-Arg), falls gewünscht.
