# Route → Endpoint Mapping

| Angular Route | Method | Backend Endpoint | Request | Response |
|---|---|---|---|---|
| `/galerie` (load) | `GET` | `/api/assets` | `page`, `page_size`, `sort` (`date\|size`), `order` (`asc\|desc`), `favourite` (bool, optional), `source[]` (repeatable), `quality_min` (0.0–1.0), `tags[]` (tag IDs, AND, repeatable), `q` (Suchtext), `q_mode` (`tags\|caption\|semantic`) | `AssetsPage { items, total, page, page_size, facets }` |
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

## Tags (P6 Phase 2 + Phase 3)

| Angular Route | Method | Backend Endpoint | Request | Response |
|---|---|---|---|---|
| Suche (Autocomplete) / `/tags` | `GET` | `/api/tags` | `query` (optional, LIKE-Filter), `page` (default 1), `page_size` (1–200, default 20) | `TagListItem[]` |
| `/tags` (Umbenennen) | `PATCH` | `/api/tags/{id}` | `{ name: string }` | `TagListItem` (409 wenn Name belegt) |
| `/tags` (Merge) | `POST` | `/api/tags/merge` | `{ from_ids: number[], into_id: number }` | `204` — from_ids werden Aliase von into_id |
| `/galerie` (Bulk-Tag via BulkBar) | `POST` | `/api/tags/bulk` | `{ asset_ids: number[], add: string[], remove: number[] }` | `204` |
| Lightbox (Tag-Edit) | `PATCH` | `/api/assets/{id}/tags` | `{ add: string[], remove: number[] }` | `AssetDetailDto` |
| Lightbox (Caption-Edit) | `PATCH` | `/api/assets/{id}/caption` | `{ caption: string }` | `AssetDetailDto` — setzt `caption_edited=true` |

```typescript
interface TagListItem { id: number; name: string; count: number; alias_of: number | null; }
```

**Alias-Auflösung:** Filter-Rail (`tags[]=`) und Tag-Suche (`q_mode=tags`) lösen Aliase auf — ein Tag mit `alias_of=X` findet Bilder, die mit X getaggt sind, und umgekehrt. `POST /api/tags/merge` setzt `alias_of` und re-pointet alle `asset_tag`-Zeilen auf den Ziel-Tag.

**Manuelle Korrekturen:** `PATCH /api/assets/{id}/tags` setzt `kind=manual` auf hinzugefügten Tags und `manually_removed=true` auf entfernten Auto-Tags. Reruns (Tagging-Job, Caption-Job) respektieren diese Flags.

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

## Modelle (P4)

| Angular Route | Method | Backend Endpoint | Request | Response |
|---|---|---|---|---|
| `/einstellungen` (model list) | `GET` | `/api/models` | — | `ModelDto[]` |
| `/einstellungen` (capabilities) | `GET` | `/api/models/capabilities` | — | `CapabilitiesDto` |
| `/einstellungen` (download) | `POST` | `/api/models/{manifest_id}/download` | `{ license_ack?: bool }` | `{ job_id: string }` |
| `/einstellungen` (scan) | `POST` | `/api/models/scan` | — | `{ registered: ScanResult[] }` |
| `/einstellungen` (in-place) | `POST` | `/api/models/register-local` | `{ manifest_id: string, path: string }` | `ModelDto` |
| `/einstellungen` (remove) | `DELETE` | `/api/models/{manifest_id}` | — | `{ deleted: bool, file_removed: bool }` |

```typescript
interface ModelDto {
  id: string;
  role: 'face' | 'tagger' | 'captioner' | 'semantic_search' | 'rembg';
  name: string;
  variant: string | null;
  format: 'onnx' | 'onnx_bundle' | 'onnx_folder';
  path: string | null;
  sha256: string | null;
  managed: boolean;
  enabled: boolean;
  is_default: boolean;
  status: 'active' | 'available' | 'missing' | 'inplace';
  size_bytes: number | null;
  license_note: string | null;
}

interface CapabilitiesDto {
  faces: boolean;
  tagging: boolean;
  captioning: boolean;
  semantic_search: boolean;
  rembg: boolean;
}

interface ScanResult {
  manifest_id: string;
  path: string;
}
```

Fehler-Codes (strukturiert im `detail`-Feld):
- `404 { code: "MODEL_NOT_FOUND" }` — `manifest_id` nicht im Manifest (auch bei `DELETE`)
- `409 { code: "LICENSE_ACK_REQUIRED", license_note: string }` — `license_ack: true` fehlt
- Job-Fehler (async, im Job-Stream): `MODEL_HASH_MISMATCH`, `MODEL_INCOMPLETE`

`POST /api/models/register-local` — In-Place-Validierung (Konzept §12.2a), fünf Stufen
in Reihenfolge: Existenz → Format → Rolle → Vollständigkeit → Ladbarkeit. Bei Fehler
`422` mit strukturiertem `detail`, das Frontend auf „erwartet · gefunden · nächster Schritt" mappt:

```typescript
// 422 detail
interface ModelValidationDetail {
  code:
    | 'MODEL_NOT_FOUND'      // Pfad existiert nicht / nicht lesbar
    | 'MODEL_WRONG_FORMAT'   // Magic-Bytes/Endung passen nicht (onnx erwartet, gguf/safetensors gefunden); auch Datei↔Ordner-Verwechslung
    | 'MODEL_WRONG_ROLE'     // ONNX-Graph passt nicht zur Slot-Rolle (nur wenn onnxruntime verfügbar)
    | 'MODEL_INCOMPLETE'     // Ordner-Modell: Pflicht-Begleitdatei fehlt (z.B. selected_tags.csv, config.json)
    | 'MODEL_LOAD_FAILED';   // Probe-Load scheitert (ONNX-Session bzw. Protobuf-Header)
  expected: string;
  found: string;
  next_step: string;
}
```

`DELETE` lässt bei In-Place-Modellen (`managed = 0`) die referenzierte Datei unangetastet
(`file_removed: false`); bei managed-Modellen werden Datei/Ordner mitgelöscht.

## Caption-Presets (P5 Phase 6)

| Angular Route | Method | Backend Endpoint | Request | Response |
|---|---|---|---|---|
| `/einstellungen` | `GET` | `/api/caption-presets` | `?model_id=` (optional) | `CaptionPresetDto[]` |
| `/einstellungen` | `POST` | `/api/caption-presets` | `CaptionPresetCreate` | `CaptionPresetDto` (201) |
| `/einstellungen` | `PATCH` | `/api/caption-presets/{id}` | `CaptionPresetUpdate` | `CaptionPresetDto` |
| `/einstellungen` | `DELETE` | `/api/caption-presets/{id}` | — | 204 |

```typescript
interface CaptionPresetDto {
  id: number;
  name: string;
  model_id: number | null;   // null = model-agnostic
  config: Record<string, unknown>;
  is_default: boolean;
}
```

Config wird gegen `caption_mode` des Modells validiert (`caption_config.py`). Default-Setzen löscht bisherigen Default im selben Modell-Scope. `ModelDto` enthält `caption_mode` und `capabilities` (deklarativer UI-Descriptor §12.6, aus Manifest).

## Klassifizierung / Rerun (P5 Phase 5)

| Angular Route | Method | Backend Endpoint | Request | Response |
|---|---|---|---|---|
| `/galerie` (Rerun einzeln) | `POST` | `/api/classify/rerun` | `RerunRequest` | `{ job_id: string }` |
| `/galerie` (Rerun alle) | `POST` | `/api/classify/rerun` | `RerunRequest` | `{ job_id: string }` |

```typescript
type ClassifyStep = 'tags' | 'caption' | 'embedding' | 'heuristics';

interface RerunRequest {
  asset_ids: number[] | 'all';   // konkrete IDs oder gesamter Bestand
  steps: ClassifyStep[];          // mindestens einen Step angeben
  caption_preset_id?: number;     // optional: Caption-Preset für den caption-Step
}
```

Verhalten:
- Ledger-Flags der gewählten Steps werden **zurückgesetzt**, dann die Schritte neu berechnet.
- Ein einzelner Batch-Job in der Queue; Fortschritt per `/api/jobs/stream` sichtbar.
- Modell deaktiviert → Schritt wird übersprungen, kein Fehler.
- Fehler: `422` wenn `steps` leer.

## Semantische Suche (P5 Phase 4)

| Angular Route | Method | Backend Endpoint | Request | Response |
|---|---|---|---|---|
| Such-UI (ab P6; bis dahin API) | `POST` | `/api/search/semantic` | `SemanticSearchRequest` | `SemanticSearchResponse` |

```typescript
// Genau eines von query / like_asset_id setzen (sonst 422).
interface SemanticSearchRequest {
  query?: string;          // Freitext → CLIP-Text-Embedding (text→image)
  like_asset_id?: number;  // „mehr wie dieses" → nutzt das gespeicherte Embedding (image→image)
  limit?: number;          // 1..100, default 24
}

interface SearchHit { asset_id: number; score: number; }   // score = Cosine-Ähnlichkeit (1.0 = identisch)
interface SemanticSearchResponse { hits: SearchHit[]; }
```

Treffer sind nach Cosine-Ähnlichkeit absteigend sortiert; soft-gelöschte Assets werden
herausgefiltert, bei `like_asset_id` ist das Quell-Asset selbst ausgeschlossen.

Fehler-Codes (strukturiert im `detail`-Feld):
- `422` — weder oder beide von `query`/`like_asset_id` gesetzt
- `404` — `like_asset_id` existiert nicht
- `409 { code: "SEMANTIC_SEARCH_UNAVAILABLE" }` — CLIP-Modell nicht aktiv (Textsuche nicht möglich)
- `409 { code: "NO_EMBEDDING" }` — `like_asset_id` hat noch kein Embedding

## Job-Stream

| Trigger | Endpoint | Protokoll |
|---|---|---|
| Job-Fortschritt (import, scan, thumbnail, backup, reconcile, rebuild, tagging, captioning, embedding) | `/api/jobs/stream` | SSE — jede Zeile ist ein `Job`-JSON |

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
