# Route → Endpoint Mapping

| Angular Route | Method | Backend Endpoint | Request | Response |
|---|---|---|---|---|
| `/galerie` (load) | `GET` | `/api/assets` | `page`, `page_size`, `sort` (`date\|size`), `order` (`asc\|desc`), `favourite` (bool, optional) | `AssetsPage { items, total, page, page_size }` |
| `/galerie` (cell thumbnail) | `GET` | `/api/assets/{id}/thumbnail` | `size` (256\|512) | JPEG blob — `ETag: "{hash}-{size}"`, `Cache-Control: immutable` |
| `/galerie` (lightbox) | `GET` | `/api/assets/{id}/file` | — | Original-Bild |
| `/galerie` (detail) | `GET` | `/api/assets/{id}` | — | `AssetDetailDto` (wie Dto + `path`) |
| `/galerie` (import) | `POST` | `/api/assets/import` | `{ paths: string[] }` | `{ job_id }` |
| `/galerie` (scan) | `POST` | `/api/assets/scan` | — | `{ job_id }` |
| `/galerie` (favourite, P5) | `PATCH` | `/api/assets/{id}/favourite` | `{ value: bool }` | aktualisiertes `AssetDto` |
| `/galerie` (trash, P5) | `DELETE` | `/api/assets/{id}` | — | Soft-Delete |
| Trash-View (P5) | `GET` | `/api/trash` | — | `AssetDto[]` (sortiert nach `deleted_at` desc) |
| Trash-View (P5) | `POST` | `/api/trash/{id}/restore` | — | wiederhergestelltes `AssetDto` |
| Trash-View (P5) | `DELETE` | `/api/trash/{id}` | — | `204` — endgültig gelöscht (Datei + Thumbnails + DB-Zeilen) |
| Trash-View (P5) | `DELETE` | `/api/trash` | — | `204` — Papierkorb leeren (alle endgültig) |

`PATCH /api/assets/{id}/favourite` und `DELETE /api/assets/{id}` liefern: Favourite → aktualisiertes `AssetDto`; Delete → `204`. `{id}` ist überall die `asset.id` (Stage 1: genau eine Instanz pro Asset).

## Job-Stream

| Trigger | Endpoint | Protokoll |
|---|---|---|
| Job-Fortschritt (import, scan, thumbnail) | `/api/jobs/stream` | SSE — jede Zeile ist ein `Job`-JSON |

## AssetDto (Frontend-Typ)

```typescript
interface AssetDto {
  id: number;
  content_hash: string;
  width: number | null;
  height: number | null;
  file_size: number | null;
  format: string | null;
  source: string | null;          // "original" | "flux" | "sdxl" | …
  created_at: string | null;      // ISO-8601
  imported_at: string | null;     // ISO-8601
  favourite: boolean;
  version_count: number;
  generation_meta: Record<string, unknown> | null;
}
```
