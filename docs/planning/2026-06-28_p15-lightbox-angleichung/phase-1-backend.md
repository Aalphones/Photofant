# Phase 1 — Backend-Erweiterungen

**Tier:** heikel
**Status:** complete

Voraussetzung für alle anderen Phasen.

---

## Kontext (was vorher lesen)

- `backend/photofant/api/assets.py` — `GET /assets/{id}`, `PATCH /assets/{id}`
- `backend/photofant/db/models.py` — `Asset`, `AssetVersion`-Klassen
- `frontend/src/app/models/asset.model.ts` — `AssetDetailDto`, `VersionDto`, `AssetSummary`
- `frontend/src/app/services/asset.service.ts` — `getAsset()`, `setAssetOriginal()`

---

## Abnahme-Kriterien

- [x] `GET /api/assets/{id}` liefert `original_id`, `linked_edits[]`, `versions[]`, `quality`, `framing`
- [x] `linked_edits` enthält alle Assets, deren `original_id == id` (als `AssetSummary`)
- [x] `versions[]` enthält alle Versionen mit `id`, `type`, `is_current`, `created_at`, `thumbnail_url`, `res`
- [x] `PATCH /api/assets/{id}` akzeptiert `source`, `framing`, `original_id` (null = Zuordnung entfernen)
- [x] Frontend `AssetDetailDto` + `AssetSummary` haben alle neuen Felder typisiert
- [x] `AssetService.patchAsset()` neu oder `setAssetOriginal()` erweitert um source/framing

---

## Checkliste

### Backend — Detail-Endpoint erweitern

- [x] `GET /api/assets/{id}` Response-Schema prüfen/erweitern:
  - `original_id: int | None` — direktes Feld auf `Asset`-Model (bereits vorhanden? prüfen)
  - `linked_edits: list[AssetSummarySchema]` — Query: `SELECT * FROM asset WHERE original_id = :id`
  - `versions: list[VersionSchema]` — bereits in `AssetVersion`-Tabelle, bisher nicht serialisiert
  - `quality: float | None` — falls im Asset-Model vorhanden (prüfen, ggf. aus `generation_meta` lesen)
  - `framing: str | None` — falls im Asset-Model vorhanden (prüfen)
- [x] `AssetSummarySchema` definieren (id, thumbnail_url, source, width, height, created_at)
- [x] `VersionSchema` definieren (id, type, parent_id, is_current, params, created_at, thumbnail_url, res)

### Backend — Patch-Endpoint erweitern

- [x] `PATCH /api/assets/{id}` Body-Schema um optionale Felder erweitern:
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
- [x] Endpoint setzt `asset.source`, `asset.framing`, `asset.original_id` wenn übergeben
- [x] Validierung: `framing` nur in `['close_up', 'medium', 'full_body', None]`

### Frontend — Models

- [x] `AssetDetailDto` in `asset.model.ts` erweitern:
  ```typescript
  original_id:   number | null
  linked_edits:  AssetSummary[]
  versions:      VersionDto[]
  quality:       number | null
  framing:       string | null
  ```
- [x] `AssetSummary`-Interface sicherstellen (id, source, width, height, created_at, thumbnail_url o.ä.)
- [x] `VersionDto` bereits vorhanden — sicherstellen dass `thumbnail_url` und `res` enthalten sind

### Frontend — AssetService

- [x] `patchAsset(id: number, patch: Partial<AssetPatch>): Observable<void>` anlegen
  - `AssetPatch`: `{ source?: string; framing?: string; original_id?: number | null }`
  - `null` für `original_id` explizit serialisieren (kein `undefined`)
- [x] Bestehende `setAssetOriginal(editId, originalId)` kann intern `patchAsset` nutzen oder bleibt

---

## Report-Back

- `versions[]` war schon vor dieser Phase implementiert (inkl. Face-Versionen über `version.face_id`) — nur `original_id`, `linked_edits`, `quality`, `framing` waren neu zu bauen.
- Frontend-Typname für die Kontrakt-`AssetSummary` heißt `AssetLinkSummary`, nicht `AssetSummary` — es gab bereits ein anders geformtes `AssetSummary`-Interface in `review.model.ts` (für Duplikat-Review), Namenskollision im Barrel wäre sonst unvermeidlich.
- Neuer generischer `PATCH /api/assets/{id}` ergänzt die bestehenden spezifischen Patch-Routen (`/favourite`, `/tags`, `/caption`, `/original`) — die bleiben unverändert bestehen, keine Migration nötig.
- `AssetDetailDto`-Aufbau in `assets.py` in `_build_asset_detail_dto()` extrahiert, damit `GET` und der neue `PATCH` dieselbe Logik teilen.
