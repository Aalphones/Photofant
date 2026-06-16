# Route → Endpoint Mapping

| Angular Route | Method | Backend Endpoint | Request | Response |
|---|---|---|---|---|
| `/galerie` (load) | `GET` | `/api/assets` | `page`, `page_size`, `sort` (`date\|size`), `order` (`asc\|desc`), `favourite` (bool, optional) | `AssetsPage { items, total, page, page_size }` |
| `/galerie` (cell thumbnail) | `GET` | `/api/assets/{id}/thumbnail` | `size` (256\|512) | JPEG blob — `ETag: "{hash}-{size}"`, `Cache-Control: immutable` |
| `/galerie` (lightbox) | `GET` | `/api/assets/{id}/file` | — | Original-Bild |
| `/galerie` (detail) | `GET` | `/api/assets/{id}` | — | `AssetDetailDto` (wie Dto + `path`) |
| `/galerie` (import — Serverpfade) | `POST` | `/api/assets/import` | `{ paths: string[] }` | `{ job_id }` |
| `/galerie` (import — Browser-Upload) | `POST` | `/api/assets/upload` | `multipart/form-data; files[]` | `{ job_id }` |
| `/galerie` (scan) | `POST` | `/api/assets/scan` | — | `{ job_id }` |
| `/galerie` (favourite, P5) | `PATCH` | `/api/assets/{id}/favourite` | `{ value: bool }` | aktualisiertes `AssetDto` |
| `/galerie` (trash, P5) | `DELETE` | `/api/assets/{id}` | — | Soft-Delete |
| Trash-View (P5) | `GET` | `/api/trash` | — | `AssetDto[]` (sortiert nach `deleted_at` desc) |
| Trash-View (P5) | `POST` | `/api/trash/{id}/restore` | — | wiederhergestelltes `AssetDto` |
| Trash-View (P5) | `DELETE` | `/api/trash/{id}` | — | `204` — endgültig gelöscht (Datei + Thumbnails + DB-Zeilen) |
| Trash-View (P5) | `DELETE` | `/api/trash` | — | `204` — Papierkorb leeren (alle endgültig) |

`PATCH /api/assets/{id}/favourite` und `DELETE /api/assets/{id}` liefern: Favourite → aktualisiertes `AssetDto`; Delete → `204`. `{id}` ist überall die `asset.id` (Stage 1: genau eine Instanz pro Asset).

## Maintenance

| Angular Route | Method | Backend Endpoint | Request | Response |
|---|---|---|---|---|
| `/einstellungen` (backup trigger) | `POST` | `/api/maintenance/backup` | `{ target_dir?: string }` | `{ job_id: string }` — BACKUP-Job in Queue |
| `/einstellungen` (backup list) | `GET` | `/api/maintenance/backups` | — | `BackupInfo[]` (neueste zuerst) |
| `/wartung` (reconcile trigger) | `POST` | `/api/maintenance/reconcile` | — | `{ job_id: string }` — RECONCILE-Job in Queue |
| `/wartung` (reconcile report) | `GET` | `/api/maintenance/reconcile/report` | — | `ReconcileReport` (leerer Report wenn noch kein Scan) |
| `/wartung` (reconcile repair) | `POST` | `/api/maintenance/reconcile/repair` | `{ actions: RepairAction[] }` | `RepairResponse` |
| `/wartung` (rebuild trigger) | `POST` | `/api/maintenance/rebuild` | `{ target: 'thumbnails' }` | `{ job_id: string }` — REBUILD-Job in Queue |
| `/wartung` (status) | `GET` | `/api/maintenance/status` | — | `MaintenanceStatus` |

```typescript
interface ReconcileReport {
  generated_at: string | null;               // ISO-8601; null = noch kein Scan
  orphaned_files: OrphanFile[];               // FS vorhanden, keine DB-Zeile
  missing_files: MissingFile[];               // DB-Zeile, FS fehlt
  path_drift: DriftFile[];                    // FS woanders gefunden (Hash-Match)
}

interface OrphanFile { path: string; size: number; person_name: string | null; detail: string; }
interface MissingFile { instance_id: number; asset_id: number; path: string; person_name: string | null; detail: string; }
interface DriftFile { instance_id: number; asset_id: number; db_path: string; found_path: string; person_name: string | null; detail: string; }

// Repair: pro Item genau eine explizit gewählte Aktion (kein Auto-Repair).
// Gültige (kind, action)-Paare: orphan→index|trash, missing→mark_missing|trash, drift→fix_path.
interface RepairItem { kind: 'orphan' | 'missing' | 'drift'; instance_id?: number; path?: string; found_path?: string; }
interface RepairAction { item: RepairItem; action: 'index' | 'mark_missing' | 'trash' | 'fix_path'; }
interface RepairResult { kind: string; action: string; status: 'ok' | 'error'; message: string | null; }
interface RepairResponse { results: RepairResult[]; import_job_id: string | null; }  // import_job_id gesetzt, wenn orphan→index Dateien neu importiert wurden
```

```typescript
interface BackupInfo {
  filename: string;
  path: string;
  size: number;        // Bytes
  created_at: string;  // ISO-8601
}

// RebuildTarget ist bewusst erweiterbar — P7 hängt 'faces' an.
type RebuildTarget = 'thumbnails';

interface MaintenanceStatus {
  db_size: number;          // db.sqlite Größe in Bytes
  thumbnail_count: number;  // Assets mit mindestens einem gecachten Thumbnail
  cache_size: number;       // thumbnails.sqlite Größe in Bytes
}
```

## Job-Stream

| Trigger | Endpoint | Protokoll |
|---|---|---|
| Job-Fortschritt (import, scan, thumbnail, backup, reconcile, rebuild) | `/api/jobs/stream` | SSE — jede Zeile ist ein `Job`-JSON |

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
