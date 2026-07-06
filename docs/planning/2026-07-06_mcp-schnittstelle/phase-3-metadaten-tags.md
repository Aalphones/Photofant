# Phase 3 — Metadaten & Tag-Vokabular (Write, non-destruktiv)

**Komplexität:** standard · **Status:** pending

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

- [ ] `tools/metadata.py` registriert:
  - [ ] `edit_tags(asset_id, add?, remove?)` → `PATCH /assets/{id}/tags`; setzt `kind=manual` (Endpoint-Logik).
  - [ ] `bulk_edit_tags(asset_ids, add?, remove?)` → `POST /tags/bulk`.
  - [ ] `set_caption(asset_id, caption)` → `PATCH /assets/{id}/caption` (`caption_edited=true`).
  - [ ] `set_photo_meta(asset_id, source?, framing?, original_id?)` → `PATCH /assets/{id}`.
  - [ ] `set_classification(asset_ids | "all", labels?)` bzw. Rerun des `categories`-Steps →
        `POST /classify/rerun` mit `steps:["categories"]`; gibt `job_id` zurück (async → `get_job_status`).
  - [ ] `list_tags(query?, page?)` → `TagListItem[]` (Namen, Count, Aliase).
  - [ ] `rename_tag(tag_id, name)` → `PATCH /tags/{id}` (409 bei Konflikt sauber melden).
  - [ ] `merge_tags(from_ids, into_id)` → `POST /tags/merge` (Aliase; re-pointet `asset_tag`).
  - [ ] `set_tag_aliases(tag_id, names)` → `PUT /tags/{id}/aliases`.
- [ ] Alle Write-Tools geben den aktualisierten Zustand knapp zurück (z. B. neue Tag-Liste des Assets),
      nicht den ganzen DTO-Dump.

## Umsetzung — Checkliste

- [ ] `tools/metadata.py` mit den Tools oben.
- [ ] Fehler-Mapping: Endpoint-`409`/`422`/`404` → verständliche Text-Antwort für den Agenten.
- [ ] Doc: `docs/routes.md` MCP-Abschnitt ergänzen.

## Report-Back
