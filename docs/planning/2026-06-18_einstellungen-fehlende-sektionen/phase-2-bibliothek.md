# Einstellungen fehlende Sektionen · Phase 2 — Bibliothek

> Rating: **standard** · Status: complete · (Rating-Abstufung: Henne-Ei-Problem entfällt durch settings.json-Infrastruktur)

## Kontext (vorher lesen)

- [README.md](README.md) — Persistenz-Entscheidung (settings.json)
- `2026-06-18_settings-json-infrastruktur` — Voraussetzung; `load_settings()`, `patch_settings()` bereits vorhanden
- `backend/photofant/config.py` — `get_data_root_base()` liest nach Infrastruktur-Plan bereits aus `settings.json`
- `frontend/src/app/store/models/` — bestehende `modelsDir`-Verdrahtung als Vorlage

## Warum kein Henne-Ei mehr

`settings.json` liegt bei `.photofant/settings.json` relativ zum Backend-CWD — einem fixen, DB-unabhängigen Pfad. `data_root` IN der Datei zeigt auf die Medienbibliothek; die DB liegt ebenfalls in `.photofant/` (selber Ordner). Kein Circular Dependency.

Außerdem enthält `data_root` alle Bilddateien — eine Änderung via UI **verschiebt keine Dateien**, der User muss das manuell tun. Klarer UI-Hinweis Pflicht.

## Akzeptanzkriterien

- `GET /api/config` liefert `data_root` (aus `settings.json`).
- `PATCH /api/config` mit `{ "data": { "data_root": "/..." } }` schreibt in `settings.json`; Response enthält `reboot_required: true`.
- Frontend zeigt "Neustart erforderlich"-Banner nach Pfadänderung.
- Keine Dateien werden automatisch verschoben — UI-Hinweis explizit: "Bilder und Datenbank müssen manuell in den neuen Ordner kopiert werden."

## Checkliste

### Backend

- [x] **`api/config.py` `patch_config()`**: wenn `data_root` in Body → nach Patch `reboot_required: true` in Response setzen (eigenes Response-Feld oder als Meta-Key)
- [x] **`api/config.py` Response-Model** `ConfigResponse` um optionales `reboot_required: bool` erweitern
- [x] Doc-Update: `docs/routes.md` — `data_root`-Key + `reboot_required`-Response dokumentieren

### Frontend

- [x] **`models.actions.ts`**: neue Action `updateDataRoot({ path })`, `updateDataRootSuccess({ path })`, `updateDataRootFailure({ error })`
- [x] **`models.reducer.ts`**: `dataRoot: string | null` zu `ModelsState`; `loadConfigSuccess` extrahiert `data_root`
- [x] **`models.effects.ts`**: neuer Effect für `updateDataRoot` → `PATCH /api/config`; setzt `rebootRequired: true` im State nach Erfolg
- [x] **`models.selectors.ts`**: `selectDataRoot`, `selectRebootRequired` exportieren
- [x] **`model.service.ts`**: Methode `updateDataRoot(path: string) -> Observable<...>`
- [x] **`einstellungen.ts`**: Sektion "Bibliothek" mit Sammlungs-Ordner (+ Warn-Hinweis "manuell kopieren") und Modell-Ordner; Reboot-Banner nach Änderung; "Modelle"-Sektion entfernt

## Hinweise

| Risiko | Gegenmaßnahme |
|---|---|
| User gibt falschen Pfad ein (Tippfehler) | Kein Exist-Check beim Schreiben — erst beim nächsten Start fällt es auf; Hinweis in UI |
| `settings.json` nicht schreibbar (Permissions) | `save_settings()` wirft `OSError` → Endpoint 500 mit klarer Message (aus Infrastruktur-Plan abgedeckt) |

## Report-Back
