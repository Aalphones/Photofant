# Einstellungen — fehlende Sektionen (Verarbeitung · Bibliothek · Tastaturkürzel · Info)

> Status: geparkt · **Voraussetzung: `2026-06-18_settings-json-infrastruktur` muss zuerst umgesetzt sein** · Darstellung-Tab bereits gebaut (2026-06-18)

Schließt die vier noch fehlenden Einstellungs-Sektionen mit echtem Backend-Durchstich. Jede Sektion bekommt eine eigene Phase.

## Persistenz-Entscheidung (einmal, für alle Phasen)

**Alle Settings in `settings.json`** — via `2026-06-18_settings-json-infrastruktur` bereitgestellt.
Pfad: `.photofant/settings.json` relativ zum Backend-CWD. Kein `app_config`-Table, keine Env-Vars.

| Kategorie | Wo gespeichert |
|---|---|
| Pipeline-Einstellungen | `settings.json` |
| Tastaturkürzel | `settings.json` als `keyboard_shortcuts`-Objekt |
| `data_root`, `models_dir` | `settings.json` |
| Versions-Info | aus `pyproject.toml` via `importlib.metadata` (read-only, kein Setting) |

## Overview

| Phase | Topic | Rating | Status |
|---|---|---|---|
| 1 | [Verarbeitung — Pipeline-Toggles + Schwellwerte](phase-1-verarbeitung.md) | standard | complete (via wd14-einstellungen-bulk-klassifizieren Phase 2) |
| 2 | [Bibliothek — data_root Startup-Config](phase-2-bibliothek.md) | standard | complete |
| 3 | [Tastaturkürzel — Backend-Persistenz](phase-3-tastaturkuerzel.md) | standard | complete |
| 4 | [Info — Versionierung + System-Details](phase-4-info-versionierung.md) | standard | pending |

## Kontrakt (Backend ↔ Frontend)

### Erweiterte `GET/PATCH /api/config` Keys (nach diesem Plan)
```
# Verarbeitung
auto_tag:             "true" | "false"      # Default: "true"
auto_caption:         "true" | "false"      # Default: "true"
auto_embed:           "true" | "false"      # Default: "true"
tagging_threshold:    "0.35"               # bereits vorhanden
blur_threshold:       "200.0"              # neu (vorher hardcode in heuristics_job.py)
import_parallel:      "2"                  # Anzahl gleichzeitiger Job-Slots (1–8)

# Bibliothek
models_dir:           "/pfad/..."          # bereits vorhanden
trash_auto_days:      "30"                 # Papierkorb-Automatik (0 = manuell)

# Tastaturkürzel
keyboard_shortcuts:   "{...JSON...}"       # JSON-Blob, Schema s.u.
```

### Startup-Config `photofant-config.json`
```json
{ "data_root": "/pfad/zur/bibliothek" }
```
Pfad: `~/.config/photofant/photofant-config.json` (Windows: `%APPDATA%\photofant\photofant-config.json`)
Gelesen **vor** DB-Öffnung; `PHOTOFANT_DATA_ROOT` Env-Var überschreibt weiterhin.
Neuer Endpoint: **`PATCH /api/config/data-root`** — schreibt Datei, Response `{ "reboot_required": true }`.

### Keyboard-Shortcuts Schema
```json
{
  "version": 1,
  "shortcuts": [
    { "action": "lightbox.prev",   "keys": ["ArrowLeft"] },
    { "action": "lightbox.next",   "keys": ["ArrowRight"] },
    { "action": "lightbox.close",  "keys": ["Escape"] },
    ...
  ]
}
```

### Info-Endpoint (erweitert)
**`GET /api/health`** — bestehend, liefert `{ status, version }`. Version kommt nach diesem Plan aus `importlib.metadata`.

Neuer Endpoint **`GET /api/info`** — liefert vollständige System-Details:
```json
{
  "version":        "0.1.0",
  "python_version": "3.12.x",
  "db_path":        "/...",
  "db_size_bytes":  42000000,
  "onnx_version":   "1.17.3",
  "last_migration": "0012",
  "gpu_name":       "NVIDIA RTX 4080",
  "vram_gb":        16,
  "cuda_version":   "12.4",
  "env_flags":      { "HF_HUB_OFFLINE": "1", "TRANSFORMERS_OFFLINE": "1" }
}
```

## Finale Akzeptanzkriterien

1. **Verarbeitung**: Auto-Tag/Caption/Embed-Toggles + Schärfe-Schwellwert in UI änderbar; Import-Job liest die Werte aus `app_config` und enqueued entsprechend selektiv.
2. **Bibliothek**: Sammlungs-Pfad-Änderung schreibt `photofant-config.json`; UI zeigt "Neustart erforderlich"-Banner; nach Neustart lädt Backend von neuem Pfad.
3. **Tastaturkürzel**: Belegungen in UI änderbar; `PATCH /api/config` mit JSON-Blob; nach Reload bleiben Kürzel erhalten.
4. **Info**: Versions-Anzeige liest aus `pyproject.toml` (via `importlib.metadata`); System-Details kommen aus neuem `/api/info`-Endpoint; keine manuell gepflegte Versionskonstante mehr.

## Smoke-Checkliste (User, am Plan-Ende)

- [ ] Auto-Tag deaktivieren → neues Bild importieren → kein Tagging-Job erscheint im Dock
- [ ] Auto-Tag wieder aktivieren → Import → Tagging-Job läuft
- [ ] Sammlungs-Pfad auf anderen Ordner ändern → `photofant-config.json` prüfen → Neustart → Backend läuft vom neuen Pfad
- [ ] Tastaturkürzel "Lightbox schließen" auf `Q` umbiegen → Reload → `Q` schließt Lightbox, `Esc` nicht mehr
- [ ] `GET /api/info` → liefert Version, DB-Größe, ONNX-Version
- [ ] Version in Info-Tab stimmt mit `pyproject.toml` überein ohne manuelles Ändern von `health.py`

## Summary

## Files touched

## Commits

## Deviations from plan

## Follow-ups

- `import_parallel` erfordert Rework des sequenziellen Job-Queues → ausgeklammert, eigene Entscheidung wenn Job-Queue überarbeitet wird
- rembg, pHash-Duplikat-Erkennung, Face-Threshold → erst wenn P7/P8 landen
- Trash-Auto-Days erfordert einen Cronjob/Scheduled-Task im Backend — ebenso ausgeklammert, eigene Phase wenn Papierkorb-Verwaltung priorisiert wird
