# Phase 1 — Backend WD14-Einstellungen

> Rating: **mechanisch** · Status: pending

## Kontext (vorher lesen)

- `backend/photofant/settings.py` — `AppSettings` TypedDict, `SETTINGS_DEFAULTS`, `_EXPECTED_TYPES`
- `backend/settings.example.json` — Template mit `_comment_*`-Feldern
- `backend/photofant/jobs/tagging_job.py` — liest aktuell `settings["tagging_threshold"]`, übergibt es an `resolve_wd14_tagger(threshold=...)`
- `backend/photofant/inference/adapters/wd14.py` — `WD14Tagger.tag()` filtert bereits ab Threshold und sortiert das Ergebnis bereits nach Score descending (Zeile 80). Kein Change nötig.

## Was genau geändert wird

### `settings.py`

`AppSettings` TypedDict: **zwei neue Keys** hinzufügen:
```python
min_probability: float  # ersetzt tagging_threshold als aktiver Key
max_tags: int
```
`tagging_threshold` bleibt im TypedDict für backward-compatibles Laden alter settings.json — wird aber von `tagging_job.py` nicht mehr ausgewertet.

`SETTINGS_DEFAULTS`: `min_probability: 0.5`, `max_tags: 30`

`_EXPECTED_TYPES`: beide Keys ergänzen (`min_probability: (float, int)`, `max_tags: int`)

### `settings.example.json`

Vor `tagging_threshold`-Block neue Einträge:
```json
"_comment_min_probability": "Minimale WD14-Konfidenz fuer Auto-Tags (0.0-1.0). Ersetzt tagging_threshold.",
"min_probability": 0.5,
"_comment_max_tags": "Maximale Anzahl Auto-Tags pro Bild, sortiert nach Konfidenz.",
"max_tags": 30,
```
`tagging_threshold`-Eintrag mit `_comment` als deprecated markieren.

### `tagging_job.py`

`_run_tagging()`, Zeilen 25–26, ersetzen:
```python
# alt:
threshold = load_settings()["tagging_threshold"]
tagger = resolve_wd14_tagger(threshold=threshold)

# neu:
settings = load_settings()
threshold = settings["min_probability"]
max_tags = settings["max_tags"]
tagger = resolve_wd14_tagger(threshold=threshold)
```

Nach `tag_scores = tagger.tag(image)` (Zeile 32):
```python
tag_scores = tag_scores[:max_tags]  # tagger sortiert bereits nach Score desc
```

🟡 **Achtung:** `min_probability` Default 0.5 ist strenger als altes `tagging_threshold` Default 0.35. Bestehende Settings-Dateien mit custom `tagging_threshold` behalten ihren Wert weiterhin in `settings.json`, aber er wird ignoriert — `min_probability` fällt auf 0.5. Bewusster Bruch zugunsten sauberer Tags.

## Akzeptanzkriterien

- `load_settings()` gibt `min_probability` und `max_tags` mit korrekten Defaults zurück.
- `PATCH /api/config` akzeptiert `min_probability` und `max_tags` (Typ-Validierung in `_EXPECTED_TYPES`).
- Tagging-Job wendet Threshold + Max-Count an; WD14-Sortierung bleibt erhalten.
- Kein Backend-Test nötig (private Profil; Smoke via Rerun in Phase 3).

## Checkliste

### Backend

- [ ] `settings.py`: `min_probability: float` und `max_tags: int` in `AppSettings`, `SETTINGS_DEFAULTS`, `_EXPECTED_TYPES`
- [ ] `settings.example.json`: neue `_comment_*`-Einträge + Werte; `tagging_threshold` als deprecated kommentieren
- [ ] `tagging_job.py`: `settings["min_probability"]` + `settings["max_tags"]` lesen; `tag_scores[:max_tags]`-Slice nach `tagger.tag()`

### Docs

- [ ] `docs/routes.md` aktualisieren: neue Config-Keys `min_probability`, `max_tags` dokumentieren

## Report-Back
