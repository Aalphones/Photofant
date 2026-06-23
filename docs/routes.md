# Route → Endpoint Mapping

| Angular Route | Method | Backend Endpoint | Request | Response |
|---|---|---|---|---|
| `/galerie` (load) | `GET` | `/api/assets` | `page`, `page_size`, `sort` (`date\|size`), `order` (`asc\|desc`), `favourite` (bool, optional), `source[]` (repeatable), `quality_min` (0.0–1.0), `tags[]` (tag IDs, AND, repeatable), `collection_id` (Mitglied einer Sammlung), `q` (Suchtext), `q_mode` (`tags\|caption\|semantic`) | `AssetsPage { items, total, page, page_size, facets }` |
| `/galerie` (cell thumbnail) | `GET` | `/api/assets/{id}/thumbnail` | `size` (256\|512\|1024) | JPEG blob — `ETag: "{hash}-{size}"`, `Cache-Control: immutable` |
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

## Tags (P6 Phase 2 + Phase 3 · ADR-005: re-homed nach /einstellungen)

| Angular Route | Method | Backend Endpoint | Request | Response |
|---|---|---|---|---|
| Suche (Autocomplete) / `/einstellungen` (Tags-Sektion) | `GET` | `/api/tags` | `query` (optional, LIKE-Filter), `page` (default 1), `page_size` (1–200, default 20) | `TagListItem[]` |
| `/einstellungen` (Tags-Sektion, Umbenennen) | `PATCH` | `/api/tags/{id}` | `{ name: string }` | `TagListItem` (409 wenn Name belegt) |
| `/einstellungen` (Tags-Sektion, Merge) | `POST` | `/api/tags/merge` | `{ from_ids: number[], into_id: number }` | `204` — from_ids werden Aliase von into_id |
| `/galerie` (Bulk-Tag via BulkBar) | `POST` | `/api/tags/bulk` | `{ asset_ids: number[], add: string[], remove: number[] }` | `204` |
| Lightbox (Tag-Edit) | `PATCH` | `/api/assets/{id}/tags` | `{ add: string[], remove: number[] }` | `AssetDetailDto` |
| Lightbox (Caption-Edit) | `PATCH` | `/api/assets/{id}/caption` | `{ caption: string }` | `AssetDetailDto` — setzt `caption_edited=true` |

```typescript
interface TagListItem { id: number; name: string; count: number; alias_of: number | null; }
```

**Alias-Auflösung:** Filter-Rail (`tags[]=`) und Tag-Suche (`q_mode=tags`) lösen Aliase auf — ein Tag mit `alias_of=X` findet Bilder, die mit X getaggt sind, und umgekehrt. `POST /api/tags/merge` setzt `alias_of` und re-pointet alle `asset_tag`-Zeilen auf den Ziel-Tag.

**Manuelle Korrekturen:** `PATCH /api/assets/{id}/tags` setzt `kind=manual` auf hinzugefügten Tags und `manually_removed=true` auf entfernten Auto-Tags. Reruns (Tagging-Job, Caption-Job) respektieren diese Flags.

## Collections / Smart-Alben (P6 Phase 4)

| Angular Route | Method | Backend Endpoint | Request | Response |
|---|---|---|---|---|
| `/alben` (Liste) | `GET` | `/api/collections` | — | `CollectionDto[]` |
| `/alben` (Neu) | `POST` | `/api/collections` | `{ name, kind?, match_mode? }` | `CollectionDetailDto` (201) |
| `/alben` (Detail) | `GET` | `/api/collections/{id}` | — | `CollectionDetailDto` (inkl. Triggern) |
| `/alben` (Smart-Toggle / Modus / Umbenennen) | `PATCH` | `/api/collections/{id}` | `{ name?, kind?, match_mode? }` | `CollectionDetailDto` — Modus-/Smart-Wechsel triggert Neubewertung |
| `/alben` (Löschen) | `DELETE` | `/api/collections/{id}` | — | `204` (Trigger + Items kaskadiert) |
| `/alben` (Trigger lesen) | `GET` | `/api/collections/{id}/triggers` | — | `TriggerDto[]` |
| `/alben` (Trigger hinzufügen) | `POST` | `/api/collections/{id}/triggers` | `CreateTriggerRequest` | `TriggerDto` (201) → Neubewertung |
| `/alben` (Trigger negate) | `PATCH` | `/api/collections/{id}/triggers/{tid}` | `{ negate: bool }` | `TriggerDto` → Neubewertung |
| `/alben` (Trigger entfernen) | `DELETE` | `/api/collections/{id}/triggers/{tid}` | — | `204` → Neubewertung |
| `/alben` (manuell neu bewerten) | `POST` | `/api/collections/{id}/reevaluate` | — | `{ job_id }` (202) |
| `/galerie` (Bulk-Bar „Zu Album") | `POST` | `/api/collections/{id}/items` | `{ asset_ids: number[] }` | `204` — als `source=manual` |
| `/alben` (Mitglied entfernen) | `DELETE` | `/api/collections/{id}/items/{asset_id}` | — | `204` |

```typescript
type CollectionKind = 'album' | 'smart_album' | 'training_set';
type MatchMode = 'any' | 'all';
type TriggerType = 'person' | 'tag' | 'caption';

interface CollectionDto {
  id: number;
  name: string;
  kind: CollectionKind;
  match_mode: MatchMode;
  member_count: number;          // aktive (nicht gelöschte) Mitglieder
  cover_asset_ids: number[];     // bis zu 4 für die Collage
}

interface TriggerDto {
  id: number;
  type: TriggerType;
  person_id: number | null;      // person-Trigger: bis P7 inaktiv (matcht nichts)
  tag_id: number | null;
  tag_name: string | null;       // aufgelöst für die Anzeige
  phrase: string | null;
  negate: boolean;
}

interface CollectionDetailDto extends CollectionDto { triggers: TriggerDto[]; }

interface CreateTriggerRequest {
  type: TriggerType;
  person_id?: number | null;     // type=person
  tag_id?: number | null;        // type=tag
  phrase?: string | null;        // type=caption
  negate?: boolean;
}
```

**Neubewertungs-Regel (Backend-intern, Konzept §10.1):** Tag-/Caption-Änderung an Asset X →
`reevaluate`-Queue-Job bewertet X gegen alle Smart-Alben; Trigger-/Modus-Änderung an Album Y →
Job bewertet Y gegen alle Assets. Smart-Mitgliedschaft materialisiert in
`collection_item.source='smart'`; manuelle Mitglieder (`source='manual'`) bleiben unberührt und
gewinnen bei Konflikt. Trigger-Logik: positive Trigger nach `match_mode` (any=ODER, all=UND),
negierte schließen aus; ohne positiven Trigger ist die Smart-Mitgliedschaft leer. Person-Trigger
existieren in Schema + UI, matchen aber bis P7 nichts. Hooks sitzen an Tag-Edit, Caption-Edit,
Bulk-Tagging, Tag-Merge, Tagging-/Caption-Job (Import + Rerun) und Trigger-CRUD.

## Config / Settings (Settings-JSON-Infrastruktur)

> Liest und schreibt `.photofant/settings.json` (kein DB-Zugriff mehr).

| Angular Route | Method | Backend Endpoint | Request | Response |
|---|---|---|---|---|
| `/einstellungen` (lesen) | `GET` | `/api/config` | — | `ConfigResponse` |
| `/einstellungen` (schreiben) | `PATCH` | `/api/config` | `ConfigPatchRequest` | `ConfigResponse` |

```typescript
interface ConfigResponse {
  data: AppSettings;
  reboot_required?: boolean | null;  // true wenn data_root geändert — Neustart erforderlich
}

interface ConfigPatchRequest {
  data: Partial<AppSettings>;
}

interface AppSettings {
  _schema_version: number;
  data_root: string | null;
  models_dir: string | null;
  auto_tag: boolean;
  auto_caption: boolean;
  auto_embed: boolean;
  min_probability: number;     // 0.0–1.0, default 0.5 — ersetzt tagging_threshold
  max_tags: number;            // default 30
  tagging_threshold: number;   // deprecated — wird ignoriert, nur backward-compat
  blur_threshold: number;
  trash_auto_days: number;     // 0 = deaktiviert
  keyboard_shortcuts: Record<string, string> | null;
  display: { locale: string; date_format: string };
}
```

Fehlende Keys in `PATCH` werden ignoriert (fehlende Keys = kein Update). Unbekannte Keys werden gespeichert (vorwärtskompatibel). Typfehler → `422`.

## System-Info

| Angular Route | Method | Backend Endpoint | Request | Response |
|---|---|---|---|---|
| `/einstellungen` (Info-Tab) | `GET` | `/api/info` | — | `InfoResponse` |

```typescript
interface InfoResponse {
  version: string;           // aus pyproject.toml via importlib.metadata
  python_version: string;    // sys.version
  db_path: string;
  db_size_bytes: number;
  cache_db_path: string;
  cache_db_size_bytes: number;
  onnx_version: string;      // onnxruntime.__version__
  last_migration: string | null; // letzte Alembic-Revision
  gpu_name: string | null;   // null wenn kein CUDA
  vram_gb: number | null;
  cuda_version: string | null;
  env_flags: Record<string, string>; // HF_HUB_OFFLINE, TRANSFORMERS_OFFLINE (nur wenn gesetzt)
}
```

## Maintenance

| Angular Route | Method | Backend Endpoint | Request | Response |
|---|---|---|---|---|
| `/einstellungen` (backup trigger) | `POST` | `/api/maintenance/backup` | `{ target_dir?: string }` | `{ job_id: string }` — BACKUP-Job in Queue |
| `/einstellungen` (backup list) | `GET` | `/api/maintenance/backups` | — | `BackupInfo[]` (neueste zuerst) |
| `/wartung` (reconcile trigger) | `POST` | `/api/maintenance/reconcile` | — | `{ job_id: string }` — RECONCILE-Job in Queue |
| `/wartung` (reconcile report) | `GET` | `/api/maintenance/reconcile/report` | — | `ReconcileReport` (leerer Report wenn noch kein Scan) |
| `/wartung` (reconcile repair) | `POST` | `/api/maintenance/reconcile/repair` | `{ actions: RepairAction[] }` | `RepairResponse` |
| `/wartung` (rebuild trigger) | `POST` | `/api/maintenance/rebuild` | `{ target: 'thumbnails' }` | `{ job_id: string }` — REBUILD-Job in Queue (löscht Cache, baut neu auf) |
| `/wartung` (thumbnail rebuild additive) | `POST` | `/api/maintenance/rebuild-thumbnails` | — | `{ job_id: string }` — THUMBNAIL_REBUILD-Job; 409 wenn bereits läuft |
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

type RebuildTarget = 'thumbnails' | 'embeddings' | 'faces';
// faces: re-extrahiert abgeleitete Face-Crops (origin != manual_original) aus Quell-Bildern

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
| `/einstellungen` (in-place) | `POST` | `/api/models/register-local` | `{ manifest_id: string, path?: string, components?: Record<string, string> }` | `RegisterLocalResponse` |
| `/einstellungen` (VRAM) | `GET` | `/api/models/vram` | — | `VramResponse` |
| `/einstellungen` (remove) | `DELETE` | `/api/models/{manifest_id}` | — | `{ deleted: bool, file_removed: bool }` |

```typescript
interface ModelDto {
  id: string;
  role: 'face' | 'tagger' | 'captioner' | 'semantic_search' | 'rembg' | 'upscaler' | 'editor' | 'heavy_captioner' | 'inpainter';
  name: string;
  variant: string | null;
  format: 'onnx' | 'onnx_bundle' | 'onnx_folder' | 'safetensors' | 'gguf';
  path: string | null;
  sha256: string | null;
  managed: boolean;
  enabled: boolean;
  is_default: boolean;
  status: 'active' | 'available' | 'missing' | 'inplace';
  size_bytes: number | null;
  license_note: string | null;
  components: Record<string, string> | null;  // Komponenten-Modelle: Key→Pfad-Map
}

interface CapabilitiesDto {
  faces: boolean;
  tagging: boolean;
  captioning: boolean;
  semantic_search: boolean;
  rembg: boolean;
  upscale: boolean;
  flux_edit: boolean;
  inpaint: boolean;
  heavy_caption: boolean;
}

interface RegisterLocalResponse {
  model: ModelDto;
  warnings: string[];   // z.B. Familien-Mismatch, VRAM-Warnung
}

interface VramResponse {
  gpu: GpuInfoDto | null;
  recommendations: VramRecommendation[];
}

interface GpuInfoDto {
  name: string;
  vram_gb: number;
}

interface VramRecommendation {
  model_id: string;
  recommended_variant: string | null;
}

interface ScanResult {
  manifest_id: string;
  path: string;
}
```

## Edit-Sessions (P8)

| Route | Method | Backend Endpoint | Request | Response |
|---|---|---|---|---|
| `/editor/:kind/:id` (Session erstellen) | `POST` | `/api/edit-sessions` | `{ target: { kind: "instance"\|"face"\|"version", id } }` | `CreateSessionResponse` |
| Editor (Session-Stand laden) | `GET` | `/api/edit-sessions/{key}` | — | `SessionStateResponse` |
| Editor (Op anwenden) | `POST` | `/api/edit-sessions/{key}/steps` | `{ op, params }` | `{ seq, preview_url }` |
| Editor (Rollback) | `POST` | `/api/edit-sessions/{key}/rollback` | `{ to_seq }` | `{ seq }` |
| Editor (Preview abrufen) | `GET` | `/api/edit-sessions/{key}/preview/{seq}` | — | JPEG (seq=0 → Original) |
| Editor (Speichern) | `POST` | `/api/edit-sessions/{key}/save` | `{ mode: "overwrite"\|"new_copy" }` | `VersionDto` (201) |
| Versionen (Aktuelle setzen) | `POST` | `/api/assets/{id}/set-current` | `{ version_id: number }` | `VersionDto` |
| Versionen (Re-Import) | `POST` | `/api/assets/{id}/versions/import` | `multipart/form-data; file` | `{ version: VersionDto }` (201) |
| Versionen (Thumbnail) | `GET` | `/api/versions/{id}/thumbnail` | `size` (256\|512\|1024) | JPEG blob |
| Versionen (Datei) | `GET` | `/api/versions/{id}/file` | — | Original-Datei |

```typescript
interface CreateSessionResponse { session_key: string; original_preview_url: string; }
interface SessionStateResponse  { session_key: string; kind: string; target_id: number; steps: StepInfo[]; }
interface StepInfo              { seq: number; op: string; params: Record<string, unknown>; }
interface ApplyStepResponse     { seq: number; preview_url: string; }

interface ResDto     { width: number; height: number; }
interface VersionDto {
  id: number;
  type: string | null;
  parent_id: number | null;
  path: string;
  is_current: boolean;
  params: Record<string, unknown> | null;
  created_at: string | null;
  res: ResDto | null;
  thumbnail_url: string;
}
```

**Op-Params (pydantic-validiert):**

| Op | Params | Hinweise |
|---|---|---|
| `crop` | `{ x, y, w, h }` — je `float 0–100` (Prozent der Bilddimensionen) | Koordinaten-Mapping: Prozent → Pixel per `round()` auf Zielauflösung |
| `rotate` | `{ dir: "cw"\|"ccw"\|"180"\|"free", angle?: float }` | `angle` nur bei `dir: "free"` (−360 bis 360°) |
| `mirror` | `{ axis: "h"\|"v" }` | |
| `pad` | `{ target: "1:1"\|"4:3"\|"16:9"\|…, color: "#000000"\|"#ffffff"\|"transparent" }` | Transparent → RGBA (PNG-Preview: weiß) |
| `convert` | `{ format: "png"\|"jpeg", quality: 1–100 }` | `quality` nur für JPEG; Alpha-Verlust bei JPEG |
| `rembg` | `{}` | Hintergrund entfernen via u2net ONNX → RGBA mit Alpha-Maske; 422 `MODEL_UNAVAILABLE` wenn Modell nicht aktiv |
| `smart_crop` | `{}` | Gesichtserkennung (SCRFD) → quadratischer Crop 3× Gesichtsgröße; 422 `MODEL_UNAVAILABLE` wenn buffalo\_l nicht aktiv |

## Bulk-Edit (P8 Phase 5)

| Angular Route | Method | Backend Endpoint | Request | Response |
|---|---|---|---|---|
| `/galerie` (Bulk-Bar → Bearbeiten) | `POST` | `/api/assets/bulk-edit` | `BulkEditRequest` | `JobStarted` (202) |

```typescript
interface BulkEditRequest {
  asset_ids: number[];
  op: 'rotate' | 'mirror' | 'convert' | 'rembg';
  params: Record<string, unknown>;  // op-spezifisch — gleiche Params wie Edit-Session-Ops
}

interface JobStarted { job_id: string; }
```

Verhalten: Erstellt pro Asset eine neue `Version` (immer `new_copy`, kein Overwrite). Op-Params werden pydantic-validiert (gleiche Regeln wie Edit-Session-Steps). Ungültige Op → `422`. Fehler pro Asset werden geloggt, Job läuft für übrige weiter. Ergebnis per `/api/jobs/stream` sichtbar.

---

**Preview-Strategie:** Arbeitskopie wird auf max 1024 px gethumbnailed, dann Ops angewendet. Prozent-Koordinaten sind auflösungsunabhängig. **Final-Render** (`POST .../save`) rendert in Originalauflösung und speichert nach `personX/edits/`. `rembg`- und `smart_crop`-Preview zeigen Schachbrett-Transparenz (RGBA auf JPEG-Preview: weiß composited).

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
    | 'MODEL_LOAD_FAILED'    // Probe-Load scheitert (ONNX-Session bzw. Protobuf-Header)
    | 'MODEL_COMPONENT_MISMATCH'  // Komponenten-Modell: Familien-Mismatch (warning, kein Hard-Gate)
    | 'MODEL_VRAM_EXCEEDED';      // VRAM-Budget überschritten (warning, kein Hard-Gate)
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

## Duplikaterkennung — Review-API (Phase 3, Plan `2026-06-19_duplikaterkennung`)

| Angular Route | Method | Backend Endpoint | Request | Response |
|---|---|---|---|---|
| Review-Tab (Duplikate) | `GET` | `/api/review/dupes` | — | `DupePairDto[]` (nur unresolved) |
| Review-Tab (Auflösen) | `PATCH` | `/api/review/dupes/{id}` | `{ resolution: DupeResolution }` | `DupePairDto` |
| Review-Tab / Action-Bar | `POST` | `/api/jobs/dupe-scan` | `{ scope: 'all' \| 'selection', asset_ids?: number[] }` | `{ job_id: string }` |
| Lightbox (Ähnliche Bilder) | `GET` | `/api/assets/{id}/similar` | — | `SimilarAssetDto[]` |

```typescript
interface AssetSummaryDto {
  id: number;
  width: number | null;
  height: number | null;
  format: string | null;
  source: string | null;
  file_size: number | null;
  created_at: string | null;
  imported_at: string | null;
}

interface DupePairDto {
  id: number;
  asset_a: AssetSummaryDto;
  asset_b: AssetSummaryDto;
  phash_distance: number;
  created_at: string;
}

interface SimilarAssetDto extends AssetSummaryDto {
  phash_distance: number;
}

type DupeResolution = 'a_is_original' | 'b_is_original' | 'delete_a' | 'delete_b' | 'dismiss';
```

Aktions-Semantik (`PATCH /api/review/dupes/{id}`):
- `a_is_original`: setzt `asset_b.original_id = asset_a.id`
- `b_is_original`: setzt `asset_a.original_id = asset_b.id`
- `delete_a` / `delete_b`: Soft-Delete des jeweiligen Assets (Datei → Papierkorb)
- `dismiss`: keine Asset-Änderung, Paar als erledigt markiert

`POST /api/jobs/dupe-scan` mit `scope='selection'` erfordert `asset_ids` (sonst `422`).

## Personen (P7 Phase 4)

| Angular Route | Method | Backend Endpoint | Request | Response |
|---|---|---|---|---|
| `/personen` (Liste) | `GET` | `/api/persons` | — | `PersonDto[]` (sortiert: benannt nach Count desc, Unbekannt zuletzt) |
| `/personen` (Umbenennen) | `PATCH` | `/api/persons/{id}` | `{ name: string }` | `PersonDto` (400 bei `is_unknown`, 422 bei leerem Namen) |
| `/galerie` (Person-Filter) | `GET` | `/api/assets` | `person_id` (int, optional) | `AssetsPage` — filtert auf `AssetInstance.person_id` |
| `/galerie` (Framing-Filter) | `GET` | `/api/assets` | `framing[]` (repeatable) | `AssetsPage` — filtert auf `Asset.framing` |

```typescript
interface PersonDto {
  id: number;
  name: string | null;
  is_unknown: boolean;
  count: number;           // nicht-gelöschte AssetInstances für diese Person
  fav_count: number;       // davon Favoriten
  portrait_face_id: number | null;  // bestes Face (höchster Score), Thumbnail via /api/faces/{id}/thumbnail
}
```

**Framing-Facette:** `GET /api/assets` liefert jetzt `facets.framings: FacetItem[]` — Liste der vorhandenen Framing-Werte (`close_up`, `medium`, `full_body`) mit Zählern. Framing wird in `heuristics_job` und `face_job` berechnet (BBox-Fläche / Bildfläche).

**Framing-Heuristik:** Nach Gesichtserkennung setzt der `face_job` `asset.framing` anhand der größten Face-BBox relativ zur Bildfläche:
- `close_up`: Verhältnis > 15 %
- `medium`: 4–15 %
- `full_body`: < 4 %

Der Rerun-Step `heuristics` liest vorhandene Face-Zeilen und aktualisiert `asset.framing` entsprechend.

## Faces — Matching, Clustering & Assignment (P7 Phase 2 + Phase 3)

| Angular Route | Method | Backend Endpoint | Request | Response |
|---|---|---|---|---|
| Lightbox (Face-Matches) | `GET` | `/api/faces/{face_id}/matches` | — | `FaceMatchDto[]` |
| Lightbox (Face-Thumbnail) | `GET` | `/api/faces/{face_id}/thumbnail` | — | JPEG blob (256 px) |
| `/einstellungen` / manuell | `POST` | `/api/faces/cluster` | — | `{ job_id: string }` |
| Lightbox / Review | `PATCH` | `/api/faces/{face_id}/assign` | `{ person_id: number }` | `AssignResultDto` |

```typescript
interface FaceMatchDto {
  person_id: number;
  person_name: string | null;
  best_face_id: number;
  score: number;            // Cosine-Ähnlichkeit (0–1)
}

interface AssignResultDto {
  face_id: number;
  old_person_id: number | null;
  new_person_id: number;
  asset_id: number | null;
}
```

**Score-Bänder** (konfigurierbar in `settings.json`):
- `face_auto_threshold` (default `0.6`): automatische Zuordnung
- `face_review_threshold` (default `0.45`): Vorschlag für Review-Queue
- darunter: `_unknown`

**`face_min_cluster_size`** (default `3`): HDBSCAN-Mindestclustergröße für Initial-Clustering.

**Inkrementelles Matching:** Läuft automatisch nach jedem Face-Job im Import-Fluss. Faces mit `fixed_person`-Instanzen werden nie automatisch umverteilt. Auto-Assignment materialisiert den Person-Ordner (Move/Copy) und verschiebt Face-Crops.

**Manuelle Zuordnung (`PATCH /faces/{id}/assign`):** Setzt `fixed_person=true` auf der Ziel-Instanz. Physischer Move: Bilddatei + Face-Crop wandern in den Ziel-Ordner. Hat die Quell-Person keine Faces mehr für das Asset, wird deren Instanz aufgeräumt. Feuert Smart-Album-Re-Evaluation.

**FS-Drop (§6.1a, Scan-Job):** Dateien in `person_{id}/photos/` oder `person_{id}/favourites/` ohne DB-Eintrag werden beim Scan erkannt und mit `fixed_person=true` importiert. Weitere erkannte Personen erhalten Kopien; die fixe Zuordnung bleibt unangetastet.

**Person-Ordner-Konvention:** `_unknown/` für den Auffang, `person_{id}/` für benannte Personen. Jeder mit Subordnern: `photos/`, `favourites/`, `faces/`, `edits/`.

Fehler-Codes:
- `404` — Face oder Ziel-Person nicht gefunden
- `409 { code: "NO_EMBEDDING" }` — Face hat noch kein Embedding

## Review-Queue — Gesichter (P7 Phase 5)

| Angular Route | Method | Backend Endpoint | Request | Response |
|---|---|---|---|---|
| `/review` (Face-Queue) | `GET` | `/api/review-queue` | — | `FaceReviewItemDto[]` |
| `/review` (Face-Entscheidung) | `POST` | `/api/review-queue/{face_id}` | `{ action, person_id? }` | `{ status }` |

```typescript
interface FaceReviewItemDto {
  id: number;
  face_id: number;
  suggested_person_id: number | null;
  suggested_person_name: string | null;
  score: number;
  asset_id: number;
  crop_url: string;
}

type FaceReviewAction = 'confirm' | 'reject' | 'reassign';
```

Aktions-Semantik (`POST /api/review-queue/{face_id}`):
- `confirm`: Zuordnung zur vorgeschlagenen Person bestätigen → physischer Move
- `reject`: Zuordnung ablehnen → Face geht zu `_unknown`
- `reassign` (mit `person_id`): Face zu einer anderen Person zuweisen

## Merge & Split (P7 Phase 5)

| Angular Route | Method | Backend Endpoint | Request | Response |
|---|---|---|---|---|
| `/personen` (Merge) | `POST` | `/api/persons/merge` | `{ from_id, into_id }` | `MergeResultDto` |
| `/personen` (Split) | `POST` | `/api/persons/{id}/split` | `{ face_ids: number[] }` | `SplitResultDto` |
| `/personen` (Faces einer Person) | `GET` | `/api/persons/{id}/faces` | — | `PersonFaceDto[]` |

```typescript
interface MergeResultDto {
  faces_moved: number;
  instances_moved: number;
}

interface SplitResultDto {
  new_person_id: number | null;
  faces_moved: number;
  instances_created: number;
}

interface PersonFaceDto {
  id: number;
  asset_id: number | null;
  crop_url: string;
  score: number | null;
  age: number | null;
}
```

**Merge:** Alle Faces und AssetInstances von `from_person` wandern physisch zu `into_person`. Quell-Person wird gelöscht, Ordner aufgeräumt. Duplikate (selbes Asset in beiden Personen) werden aufgelöst.

**Split:** Ausgewählte Faces werden in eine neue Person verschoben. Wenn die Quell-Person kein Face mehr für ein Asset hat, wird die Instanz verschoben statt kopiert.

## Face-Import & Duplikat-Suche (P7 Phase 6)

| Angular Route | Method | Backend Endpoint | Request | Response |
|---|---|---|---|---|
| `/personen` (Bilder importieren) | `POST` | `/api/persons/{id}/import` | `multipart/form-data; files[]` | `{ job_id: string }` — IMPORT-Job mit `fixed_person=True` |
| `/personen` (Face-Import) | `POST` | `/api/faces/import` | `multipart/form-data; files[], person_id? (Form-Feld)` | `FaceImportResult[]` |
| `/personen` (Duplikate suchen) | `POST` | `/api/duplicates/search` | `{ person_id, threshold? }` | `PersonDupePair[]` |

```typescript
interface FaceImportResult {
  face_id: number;
  person_id: number | null;
  has_embedding: boolean;
}

interface PersonDupePair {
  asset_a_id: number;
  asset_b_id: number;
  phash_distance: number;
  similarity_pct: number;  // 0–100, berechnet aus Hamming-Distanz (64 Bit)
}
```

**`POST /api/persons/{id}/import`:** Speichert Dateien in `person_{id}/photos/` und startet einen Import-Job mit `fixed_person=True` für alle importierten Instanzen.

**`POST /api/faces/import`:** Das Bild IST der Face-Crop (`origin = manual_original`, `asset_id = NULL`). ArcFace berechnet das Embedding direkt (kein Detection-Schritt). Vollständig matchbar und nie durch Face-Rebuild überschreibbar.

**`POST /api/duplicates/search`:** pHash-Hamming-Vergleich aller Instanzen einer Person. `threshold` (default 10, max 20) = maximale Hamming-Distanz (64 Bit). `similarity_pct = round((1 - distance/64) * 100)`.

**Rebuild-Target `faces`:** `POST /api/maintenance/rebuild` mit `{ target: "faces" }` re-extrahiert alle abgeleiteten Face-Crops aus den Quell-Bildern (BBox + Padding). Faces mit `origin = manual_original` bleiben unberührt.

## Job-Stream

| Trigger | Endpoint | Protokoll |
|---|---|---|
| Job-Fortschritt (import, scan, thumbnail, backup, reconcile, rebuild, tagging, captioning, embedding, face, clustering) | `/api/jobs/stream` | SSE — jede Zeile ist ein `Job`-JSON |

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
  version_count: number;          // Anzahl gespeicherter Versionen für diese Instanz
  generation_meta: Record<string, unknown> | null;
}

interface AssetDetailDto extends AssetDto {
  path: string | null;
  tags: TagDto[];
  tagger: string | null;
  caption: string | null;
  captioner: string | null;
  caption_preset_id: number | null;
  faces: FaceDto[];
  versions: VersionDto[];         // alle Versionen (Instance + Face) für dieses Asset
}
```
