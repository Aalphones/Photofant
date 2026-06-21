# Data Model Reference — Photofant

> Source of truth: `docs/Konzept-Photofant.md` §5. This file is the quick-reference for existing tables. Update after each migration.

---

## Tables (main DB — `.photofant/db.sqlite`)

> DB-Pfad konfigurierbar via `db_path` in `settings.json` (default `null` → `<data_root>/.photofant/db.sqlite`). Sowohl das Backend als auch die Alembic-Migrationen lesen ihn von dort.

### `reconcile_report` (migration 0013)

Singleton table (exactly one row, `id = 1`) holding the latest reconcile scan as a
JSON blob. Replaces the former `app_config`-blob storage.

| Column | Type | Notes |
|---|---|---|
| `id` | INTEGER PK | `CHECK (id = 1)` — singleton |
| `payload` | TEXT | JSON-serialized `ReconcileReport`, not null |
| `created_at` | DATETIME | when the report was persisted, not null |

> **`app_config` (migration 0001) was dropped in migration 0013.** All user settings now
> live in `.photofant/settings.json` (see `photofant/settings.py`), not the DB.

### `person` (migration 0002)

| Column | Type | Notes |
|---|---|---|
| `id` | INTEGER PK | |
| `name` | TEXT | nullable; `_unknown` for the seed row |
| `is_unknown` | BOOLEAN | `1` for the `_unknown` catch-all person |

Seed row: `id=1, name='_unknown', is_unknown=1` — inserted by migration 0002.

### `asset` (migration 0002)

One row per unique content-hash (canonical image).

| Column | Type | Notes |
|---|---|---|
| `id` | INTEGER PK | |
| `content_hash` | TEXT UNIQUE | SHA-256 hex; indexed |
| `source` | TEXT | `original \| sdxl \| flux \| ai_generated` |
| `width` | INTEGER | pixels |
| `height` | INTEGER | pixels |
| `file_size` | INTEGER | bytes |
| `format` | TEXT | `png \| jpeg \| webp \| …` |
| `framing` | TEXT | `close_up \| medium \| full_body \| …` (filled in P5) |
| `quality_score` | REAL | (filled in P5) |
| `age` | INTEGER | from `buffalo_l` (filled in P7) |
| `caption` | TEXT | Florence-2 caption (filled in P5 Phase 3) |
| `captioner` | TEXT | captioner manifest_id, e.g. `florence-2-base` (P5 Phase 3) |
| `caption_preset_id` | INTEGER FK → `caption_preset.id` | provenance: which preset produced the caption (FK added P5 Phase 4, `fk_asset_caption_preset`) |
| `tagger` | TEXT | model name (filled in P5) |
| `generation_meta` | JSON | raw ComfyUI workflow / A1111 parameters |
| `clip_embedding` | BLOB | CLIP ViT-L/14 image embedding, float32 unit-norm bytes (768-dim); source of truth for the vector index (P5 Phase 4) |
| `caption_edited` | BOOLEAN | `1` = Caption wurde manuell editiert; Captioner überspringt den Asset beim nächsten Rerun (P6 Phase 3) |
| `phash` | INTEGER | 64-Bit DHash-Fingerabdruck (imagehash, `hash_size=8`); NULL bis pHash-Job gelaufen (migration 0014) |
| `original_id` | INTEGER FK → `asset.id` | gesetzt wenn dieses Asset ein Edit eines anderen ist — bei Review-Entscheidung „A/B ist Original" (migration 0014) |
| `created_at` | DATETIME | EXIF capture date; UTC naive |
| `imported_at` | DATETIME | import timestamp; UTC naive; indexed |
| `processed_at` | DATETIME | last full pipeline run |

Indexes: `ix_asset_content_hash` (unique), `ix_asset_created_at`.

### `asset_instance` (migration 0002)

Physical copy per person. After clustering/assignment, one asset can have multiple
instances (one per person). Folder convention: `_unknown/` for the catch-all person,
`person_{id}/` for named persons; each with subfolders `photos/`, `favourites/`,
`faces/`, `edits/`.

**Multi-instance semantics (P7 Phase 3):** When clustering assigns an asset's faces to
real persons, the `_unknown` instance is **moved** to the first person (row reused,
file moved), and additional persons get **copies** (new rows, files copied). A manually
dropped file (`fixed_person=true`) stays put; only copies are created for other persons.
Manual face reassignment (`PATCH /faces/{id}/assign`) sets `fixed_person=true` on the
target instance and cleans up the source person's instance if no faces remain.

| Column | Type | Notes |
|---|---|---|
| `id` | INTEGER PK | |
| `asset_id` | INTEGER FK → `asset.id` | |
| `person_id` | INTEGER FK → `person.id` | |
| `path` | TEXT | absolute path; follows moves |
| `favourite` | BOOLEAN | mirrors physical location in `favourites/` (P5: toggled via physical move) |
| `fixed_person` | BOOLEAN | manually sorted — no auto-redistribution |
| `deleted_at` | DATETIME | soft-delete; NULL = active; indexed |
| `missing_at` | DATETIME | reconcile marker (migration 0003); NULL = present; a timestamp = acknowledged-missing, hidden from the next FS↔DB scan |

Unique constraint: `(asset_id, person_id)`. Index: `ix_asset_instance_deleted_at`.

**`path` + `deleted_at` semantics (P5).** `path` always tracks the file's *actual* on-disk
location and is rewritten on every physical move (favourite, soft-delete, restore).
Soft-delete sets `deleted_at` and moves the file into `<data_root>/.photofant/trash/`,
**mirroring the data-root-relative tree** (e.g. `_unknown/photos/<hash>.png` →
`.photofant/trash/_unknown/photos/<hash>.png`) so a restore can reconstruct the original
path with no extra column. Order is always *filesystem-first, then a single DB commit*;
the move helper (`photofant/media/moves.py`) is restartable (source gone + dest present →
adopt dest) so a crash between move and commit leaves only forward-recoverable drift
(detected by P3 reconciliation). Final delete removes file + thumbnails + the
`asset_instance` row, plus the `asset` + `processing_ledger` rows once the asset's last
instance is gone.

### `processing_ledger` (migration 0002)

Once-only guarantee per content-hash.

| Column | Type | Notes |
|---|---|---|
| `content_hash` | TEXT PK | |
| `faces_done` | BOOLEAN | (set in P7) |
| `tags_done` | BOOLEAN | (set in P5) |
| `caption_done` | BOOLEAN | (set in P5) |
| `embedding_done` | BOOLEAN | CLIP embedding computed (migration 0007, set in P5 Phase 4) |
| `classified` | BOOLEAN | (set in P5) |

### `model_registry` (migration 0004)

Core + optional AI models known to the app. Each row links to a manifest entry via `manifest_id`.

| Column | Type | Notes |
|---|---|---|
| `id` | INTEGER PK | |
| `manifest_id` | TEXT UNIQUE | matches `id` in `manifest.json` |
| `role` | TEXT | `face \| tagger \| captioner \| semantic_search \| rembg` |
| `name` | TEXT | display name |
| `variant` | TEXT | `default \| fp16 \| fp8 \| gguf-q4 \| …` |
| `format` | TEXT | `onnx \| onnx_bundle \| onnx_folder \| safetensors \| gguf` |
| `path` | TEXT | absolute path to file or folder; NULL for component-only models |
| `components` | JSON | named component paths (e.g. Flux: `{"diffusion": …, "text_encoder": …, "vae": …}`) |
| `sha256` | TEXT | managed: verified at download; in-place: informative only |
| `managed` | BOOLEAN | `1` = app manages file in `models_dir`; `0` = in-place reference, never touched |
| `caption_mode` | TEXT | captioner only: `task_token \| instruct \| instruct_guided` (§12.6) |
| `capabilities` | JSON | declarative UI descriptor for settings panel |
| `enabled` | BOOLEAN | `0` = downloaded but not active; `1` = active |
| `is_default` | BOOLEAN | default selection per role |

Status semantics (computed by `GET /api/models`, never stored):
- `missing` — no registry row, or managed+enabled but path gone
- `available` — managed, file present, `enabled=0`
- `active` — managed, file present, `enabled=1`
- `inplace` — `managed=0` (external reference; enabled state shown separately)

### `caption_preset` (migration 0004)

Named, reusable captioner configurations. See §12.6.

| Column | Type | Notes |
|---|---|---|
| `id` | INTEGER PK | |
| `name` | TEXT | e.g. "Natürliche Sprache", "Danbooru-Tags" |
| `model_id` | INTEGER FK → `model_registry.id` | NULL = cross-model preset |
| `config` | JSON | mode-specific config (task-token / system-prompt / builder blocks + sampling) |
| `is_default` | BOOLEAN | default preset per captioner (cleared on the previous default within the same model scope) |
| `created_at` | DATETIME | UTC naive |

Seed presets (migration 0006, model-agnostic `task_token`): **Kurz** (`<CAPTION>`, 256 tokens) and **Detailliert** (`<DETAILED_CAPTION>`, 1024 tokens, global default). CRUD: `GET/POST /api/caption-presets`, `PATCH/DELETE /api/caption-presets/{id}` — config is validated against the model's `caption_mode` (`photofant/inference/caption_config.py`).

---

### `tag` (migration 0005, erweitert 0011)

Deduplicated vocabulary; one row per unique tag name (canonical form: lowercase + underscores).

| Column | Type | Notes |
|---|---|---|
| `id` | INTEGER PK | |
| `name` | TEXT UNIQUE | lowercase + underscores (e.g. `long_hair`); display: replace `_` with space |
| `alias_of` | INTEGER FK → `tag.id` | NULL = kanonischer Tag; gesetzt durch `POST /api/tags/merge` (P6 Phase 3) |

Indexes: `ix_tag_name` (unique), `ix_tag_alias_of`.

### `asset_tag` (migration 0005)

Many-to-many join between assets and tags.

| Column | Type | Notes |
|---|---|---|
| `id` | INTEGER PK | |
| `asset_id` | INTEGER FK → `asset.id` | |
| `tag_id` | INTEGER FK → `tag.id` | |
| `kind` | TEXT | `auto` (WD14) \| `manual` (P6) |
| `score` | REAL | confidence from WD14 (nullable for manual tags) |
| `manually_removed` | BOOLEAN | `1` = User hat diesen Tag entfernt; Tagging-Job fügt ihn nicht wieder hinzu (P6 Phase 3) |

Unique constraint: `(asset_id, tag_id)`. Index: `ix_asset_tag_asset_id`.

### `vec_asset_embedding` (migration 0007)

sqlite-vec `vec0` virtual table — the searchable CLIP vector index (ADR-001). Rowid =
`asset.id`; one row per embedded asset. The canonical embedding lives on
`asset.clip_embedding` (BLOB); this table is a **rebuildable** index over those BLOBs
(`photofant/db/vector_index.py:rebuild_index`). Persists in `db.sqlite`, so it survives a
restart with no reconstruction. Maintained on import (insert) and final delete (remove);
not part of `Base.metadata` — created only by the migration, so code that touches it
degrades gracefully when the table is absent (e.g. throw-away test DBs).

| Column | Type | Notes |
|---|---|---|
| `rowid` | INTEGER | = `asset.id` |
| `embedding` | `float[768]` | `distance_metric=cosine`; cosine similarity = `1 − distance` |

> Requires the sqlite-vec loadable extension, loaded per connection via the SQLAlchemy
> `connect` event (`photofant/db/engine.py`) and inside migration 0007 (`op.get_bind()`).

### `vec_face_embedding` (migration 0016)

sqlite-vec `vec0` virtual table — the searchable ArcFace vector index for face clustering
and matching. Rowid = `face.id`; one row per face with an embedding. The canonical embedding
lives on `face.embedding` (BLOB); this table is a **rebuildable** index over those BLOBs
(`photofant/db/face_vector_index.py:rebuild_index`). Same pattern as `vec_asset_embedding`.

| Column | Type | Notes |
|---|---|---|
| `rowid` | INTEGER | = `face.id` |
| `embedding` | `float[512]` | `distance_metric=cosine`; cosine similarity = `1 − distance` |

> Maintained on face creation (face_job) and deletion; populated from existing BLOBs
> during migration 0016. Used by `GET /api/faces/{id}/matches` and incremental matching.

### `collection` (migration 0012)

Albums, training sets and smart albums (Konzept §5/§10.1). One album type: `kind = 'album'`
is hand-curated, `kind = 'smart_album'` is trigger-filled (and may still carry manual members).

| Column | Type | Notes |
|---|---|---|
| `id` | INTEGER PK | |
| `name` | TEXT | display name |
| `kind` | TEXT | `album \| smart_album \| training_set` (training_set is schema-only until P10) |
| `match_mode` | TEXT | smart_album only: `any` (OR) \| `all` (AND) |
| `settings` | JSON | training_set only (trigger_word, prefix, suffix, split …); NULL otherwise |

### `smart_trigger` (migration 0012)

A trigger that auto-fills a smart album. Positive triggers combine via `collection.match_mode`;
negated triggers exclude. Evaluation: `photofant/collections/engine.py`.

| Column | Type | Notes |
|---|---|---|
| `id` | INTEGER PK | |
| `collection_id` | INTEGER FK → `collection.id` | indexed |
| `type` | TEXT | `person \| tag \| caption` |
| `person_id` | INTEGER FK → `person.id` | set when `type=person`; **inactive until P7** (matches nothing yet) |
| `tag_id` | INTEGER FK → `tag.id` | set when `type=tag`; aliases resolved, `manually_removed` excluded |
| `phrase` | TEXT | set when `type=caption`; case-insensitive substring match on `asset.caption` |
| `negate` | BOOLEAN | `1` = exclude matches instead of include |

### `collection_item` (migration 0012)

Membership rows. Smart membership is materialized (`source='smart'`) and recomputed by the
re-evaluation engine; hand-picked rows (`source='manual'`) are never auto-removed and win on
conflict (a manual member that also matches the triggers stays `manual`).

| Column | Type | Notes |
|---|---|---|
| `collection_id` | INTEGER PK, FK → `collection.id` | |
| `asset_id` | INTEGER PK, FK → `asset.id` | indexed |
| `source` | TEXT | `manual` (hand-picked) \| `smart` (auto via triggers) |
| `caption_override` | TEXT | training sets only |

PK: `(collection_id, asset_id)`. Index: `ix_collection_item_asset_id`.

**Re-evaluation triggers (Konzept §10.1):** a tag/caption change on an asset re-evaluates that
asset against every smart album; a trigger / match-mode change re-evaluates the whole album.
Both run as `reevaluate` queue jobs (`photofant/jobs/collections_job.py`) so the UI never blocks.
Hooks sit on: `PATCH /assets/{id}/tags`, `PATCH /assets/{id}/caption`, `POST /tags/bulk`,
`POST /tags/merge`, the tagging/caption jobs (covers import + rerun), and the trigger CRUD endpoints.

---

### `review_item` (migration 0014)

Offene Duplikat-Paare, die der User manuell entscheiden soll. Erweiterbar für andere Review-Typen (z.B. Gesichts-Zuordnung in P7).

| Column | Type | Notes |
|---|---|---|
| `id` | INTEGER PK | |
| `type` | TEXT | `dupe_candidate` (erweiterbar) |
| `asset_a_id` | INTEGER FK → `asset.id` | immer der mit der kleineren ID |
| `asset_b_id` | INTEGER FK → `asset.id` | immer der mit der größeren ID |
| `phash_distance` | INTEGER | Hamming-Distanz (0–63) |
| `created_at` | DATETIME | UTC naive; nicht null |
| `resolved_at` | DATETIME | nullable; gesetzt bei Entscheidung |
| `resolution` | TEXT | nullable: `a_is_original` · `b_is_original` · `delete_a` · `delete_b` · `dismiss` |

Unique-Constraint: `uq_review_item_pair` auf `(type, asset_a_id, asset_b_id)` — kein Doppeleintrag pro Paar.

Flow: Import berechnet pHash → `find_similar` findet Treffer ≤ `dupe_threshold` → ein `review_item` pro Paar wird angelegt → User entscheidet im Review-Tab (Phase 5).

---

### `face` (migration 0015)

Erkannte Gesichter mit Crop-Pfad, Embedding und Provenienz. Ein Face gehört immer zu einer Person (initial `_unknown`).

| Column | Type | Notes |
|---|---|---|
| `id` | INTEGER PK | |
| `asset_id` | INTEGER FK → `asset.id` | `NULL` = eigenständiges Face ohne Original (P7 Phase 6) |
| `person_id` | INTEGER FK → `person.id` | initial `_unknown.id`, nach Clustering gesetzt |
| `source_version_id` | INTEGER | nullable; FK → `version.id` (P8) |
| `crop_path` | TEXT | Pfad zu `personX/faces/<asset_id>_<idx>.jpg` |
| `bbox` | JSON | `{x1, y1, x2, y2}` in Original-Bildkoordinaten |
| `padding` | INTEGER | px Padding um BBox beim Crop |
| `embedding` | BLOB | ArcFace 512-d float32, L2-normiert |
| `phash` | TEXT | DHash des Crops (für Crop-Dedupe) |
| `score` | REAL | Detection-Confidence (0–1) von buffalo_l |
| `age` | INTEGER | Altersschätzung aus buffalo_l genderage |
| `origin` | TEXT | `derived` (aus Import) \| `manual_original` (direkt importiert) |
| `origin_type` | TEXT | `original` \| `upscale` \| `flux_edit` |
| `is_upscaled` | BOOLEAN | `0` default |
| `resolution` | INTEGER | Crop-Pixel (height × width) |
| `created_at` | DATETIME | UTC naive |

Indizes: `ix_face_asset_id`, `ix_face_person_id`.

---

### `version` (migration 0018)

Saved edit versions per asset_instance or face. Exactly one of `instance_id`/`face_id` is set (XOR constraint). `parent_id` chains edits-of-edits. `is_current` marks the active version for display in gallery/lightbox.

| Column | Type | Notes |
|---|---|---|
| `id` | INTEGER PK | |
| `instance_id` | INTEGER FK → `asset_instance.id` | gesetzt: Edit eines Fotos; XOR mit `face_id` |
| `face_id` | INTEGER FK → `face.id` | gesetzt: Edit eines Faces; XOR mit `instance_id` |
| `type` | TEXT | `crop \| rotate \| mirror \| pad \| rembg \| convert \| smart_crop \| import \| edit` |
| `parent_id` | INTEGER FK → `version.id` | Edit eines Edits → Kette; NULL = erste Version |
| `path` | TEXT | Datei in `personX/edits/`, nicht null |
| `is_current` | BOOLEAN | `0` default; genau eine Version pro instance/face ist `1` |
| `params` | JSON | `{ steps: [{op, params}], width, height }` |
| `created_at` | DATETIME | UTC naive |

Indexes: `ix_version_instance_id`, `ix_version_face_id`. Check constraint: `ck_version_xor`.

---

## Upcoming tables (planned)

| Table | Migration | Plan |
|---|---|---|
| `prompt_template` | tbd | P9 |

---

## Cache DB (`.photofant/thumbnails.sqlite`) — Phase 2

Separate SQLite file; no Alembic — schema created via `CREATE TABLE IF NOT EXISTS` on first access. Throwaway cache: safe to delete and regenerate without touching `db.sqlite`.

### `thumbnail`

| Column | Type | Notes |
|---|---|---|
| `target_kind` | TEXT | `asset \| face \| edit` |
| `target_id` | INTEGER | `asset.id` for kind=asset |
| `size` | INTEGER | `256` or `512` (px, longest edge) |
| `blob` | BLOB | JPEG bytes |

PK: `(target_kind, target_id, size)`.

Path configurable via `cache_db_path` in `settings.json` (default `null` → `<data_root>/.photofant/thumbnails.sqlite`); mirrors `db_path` for the main DB.
