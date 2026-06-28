# Phase 1 — Backend-Erweiterungen

**Tier:** heikel
**Status:** pending

Voraussetzung für alle anderen Phasen.

---

## Kontext (was vorher lesen)

- `backend/photofant/api/assets.py` — `GET /assets/{id}`, `PATCH /assets/{id}`
- `backend/photofant/db/models.py` — `Asset`, `AssetVersion`-Klassen
- `frontend/src/app/models/asset.model.ts` — `AssetDetailDto`, `VersionDto`, `AssetSummary`
- `frontend/src/app/services/asset.service.ts` — `getAsset()`, `setAssetOriginal()`

---

## Abnahme-Kriterien

- [ ] `GET /api/assets/{id}` liefert `original_id`, `linked_edits[]`, `versions[]`, `quality`, `framing`
- [ ] `linked_edits` enthält alle Assets, deren `original_id == id` (als `AssetSummary`)
- [ ] `versions[]` enthält alle Versionen mit `id`, `type`, `is_current`, `created_at`, `thumbnail_url`, `res`
- [ ] `PATCH /api/assets/{id}` akzeptiert `source`, `framing`, `original_id` (null = Zuordnung entfernen)
- [ ] Frontend `AssetDetailDto` + `AssetSummary` haben alle neuen Felder typisiert
- [ ] `AssetService.patchAsset()` neu oder `setAssetOriginal()` erweitert um source/framing

---

## Checkliste

### Backend — Detail-Endpoint erweitern

- [ ] `GET /api/assets/{id}` Response-Schema prüfen/erweitern:
  - `original_id: int | None` — direktes Feld auf `Asset`-Model (bereits vorhanden? prüfen)
  - `linked_edits: list[AssetSummarySchema]` — Query: `SELECT * FROM asset WHERE original_id = :id`
  - `versions: list[VersionSchema]` — bereits in `AssetVersion`-Tabelle, bisher nicht serialisiert
  - `quality: float | None` — falls im Asset-Model vorhanden (prüfen, ggf. aus `generation_meta` lesen)
  - `framing: str | None` — falls im Asset-Model vorhanden (prüfen)
- [ ] `AssetSummarySchema` definieren (id, thumbnail_url, source, width, height, created_at)
- [ ] `VersionSchema` definieren (id, type, parent_id, is_current, params, created_at, thumbnail_url, res)

### Backend — Patch-Endpoint erweitern

- [ ] `PATCH /api/assets/{id}` Body-Schema um optionale Felder erweitern:
  ```python
  class AssetPatchBody(BaseModel):
      source:      str | None = None
      framing:     str | None = None
      original_id: int | None = None   # -1 oder "remove" als Signal?
  ```
  🟡 Für „Zuordnung entfernen" brauchen wir ein explizites Signal — entweder `original_id: null`
  in JSON oder einen separaten `DELETE /assets/{id}/original`. Empfehlung: nullable int in PATCH
  (null = entfernen), aber das erfordert dass null und „nicht übergeben" unterscheidbar sind
  (Pydantic `model_fields_set` / `exclude_unset`).
- [ ] Endpoint setzt `asset.source`, `asset.framing`, `asset.original_id` wenn übergeben
- [ ] Validierung: `framing` nur in `['close_up', 'medium', 'full_body', None]`

### Frontend — Models

- [ ] `AssetDetailDto` in `asset.model.ts` erweitern:
  ```typescript
  original_id:   number | null
  linked_edits:  AssetSummary[]
  versions:      VersionDto[]
  quality:       number | null
  framing:       string | null
  ```
- [ ] `AssetSummary`-Interface sicherstellen (id, source, width, height, created_at, thumbnail_url o.ä.)
- [ ] `VersionDto` bereits vorhanden — sicherstellen dass `thumbnail_url` und `res` enthalten sind

### Frontend — AssetService

- [ ] `patchAsset(id: number, patch: Partial<AssetPatch>): Observable<void>` anlegen
  - `AssetPatch`: `{ source?: string; framing?: string; original_id?: number | null }`
  - `null` für `original_id` explizit serialisieren (kein `undefined`)
- [ ] Bestehende `setAssetOriginal(editId, originalId)` kann intern `patchAsset` nutzen oder bleibt

---

## Report-Back

_Hier trägt der Umsetzer nach Abschluss ein was abwich oder auffiel._
