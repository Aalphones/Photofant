# Phase 3 — Metadaten & Tag-Vokabular (Write, non-destruktiv)

**Komplexität:** standard · **Status:** complete

## Kontext (vor dem Bauen lesen)

- `README.md` — Kontrakt (Rückgabe-Format). Diese Phase hat **keine** destruktiven Tools → kein Gate.
- `phase-1` / `phase-2` — etabliertes Tool-Muster.
- `backend/photofant/api/assets.py` — `PATCH /assets/{id}/tags`, `/caption`, `PATCH /assets/{id}`
  (source/framing/original), `POST /tags/bulk`.
- `backend/photofant/api/tags.py` — `list_tags`, `rename_tag` (`PATCH /tags/{id}`), `merge_tags`
  (`POST /tags/merge`), `set_aliases` (`PUT /tags/{id}/aliases`).
- `backend/photofant/api/classify.py` — `POST /classify/rerun` (Step `categories` u. a.).
- `docs/routes.md` — Abschnitte „Tags", „Klassifizierung / Rerun".

## AK (falsifizierbar)

- [x] `tools/metadata.py` registriert:
  - [x] `edit_tags(asset_id, add?, remove?)` → `PATCH /assets/{id}/tags`; setzt `kind=manual` (Endpoint-Logik).
  - [x] `bulk_edit_tags(asset_ids, add?, remove?)` → `POST /tags/bulk`.
  - [x] `set_caption(asset_id, caption)` → `PATCH /assets/{id}/caption` (`caption_edited=true`).
  - [x] `set_photo_meta(asset_id, source?, framing?, original_id?)` → `PATCH /assets/{id}`.
  - [x] `set_classification(asset_ids | "all", steps?)` → `POST /classify/rerun` (Default `steps:["categories"]`);
        gibt `job_id` zurück (async → `get_job_status`). **Deviation:** Plan-Bullet nannte `labels?` — der
        Rerun-Endpoint kennt keine Label-Filterung, nur `steps`. Statt eines nicht-existenten Parameters wird
        `steps` direkt durchgereicht (Default `["categories"]`, Agent kann zusätzlich `tags`/`caption`/`embedding`/
        `heuristics`/`faces` anfordern — deckt sich mit dem Kontext-Hinweis „Step categories u. a.").
  - [x] `list_tags(query?, page?)` → `TagListItem[]` (Namen, Count, Aliase). **Ergänzung:** `total` (Kontrakt-Pflicht
        für Listen-Tools) wird per eigener Count-Query ermittelt — der HTTP-Endpoint liefert kein `total`.
  - [x] `rename_tag(tag_id, name)` → `PATCH /tags/{id}` (409 bei Konflikt sauber melden).
  - [x] `merge_tags(from_ids, into_id)` → `POST /tags/merge` (Aliase; re-pointet `asset_tag`).
  - [x] `set_tag_aliases(tag_id, names)` → `PUT /tags/{id}/aliases`.
- [x] Alle Write-Tools geben den aktualisierten Zustand knapp zurück (z. B. neue Tag-Liste des Assets),
      nicht den ganzen DTO-Dump.

## Umsetzung — Checkliste

- [x] `tools/metadata.py` mit den Tools oben.
- [x] Fehler-Mapping: Endpoint-`409`/`422`/`404` → verständliche Text-Antwort für den Agenten
      (generischer `_run_or_error()`-Helper, fängt `HTTPException` ab).
- [x] Doc: `docs/routes.md` MCP-Abschnitt ergänzen.

## Report-Back

- `tools/metadata.py`: 9 Write-Tools (edit_tags, bulk_edit_tags, set_caption, set_photo_meta,
  set_classification, list_tags, rename_tag, merge_tags, set_tag_aliases). Ruff + mypy grün.
- `set_photo_meta`: `source`/`framing` haben keinen Clear-Pfad (nie sinnvoll leer); `original_id`
  braucht `clear_original=true` für explizites Löschen der Zuordnung — via `AssetPatchBody.model_validate()`
  statt `**kwargs`, damit `model_fields_set` (Endpoint-Kontrakt „nur gesetzte Felder ändern") korrekt bleibt.
- Zwei Deviations vom Plan-Wortlaut (siehe AK oben): `set_classification` nutzt `steps` statt des nicht
  existierenden `labels`-Parameters; `list_tags` ergänzt `total` per Zusatz-Query.
- Kein Live-Smoke gegen echte DB in dieser Phase (private-Profil: Smoke-Abgleich einmal am Plan-Ende,
  durch den User).
