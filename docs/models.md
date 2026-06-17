# Data Model Reference — Photofant

> Source of truth: `docs/Konzept-Photofant.md` §5. This file is the quick-reference for existing tables. Update after each migration.

---

## Tables (main DB — `.photofant/db.sqlite`)

### `app_config` (migration 0001)

| Column | Type | Notes |
|---|---|---|
| `key` | TEXT PK | e.g. `data_root`, `models_dir` |
| `value` | TEXT | nullable |

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
| `caption` | TEXT | (filled in P5) |
| `captioner` | TEXT | model name (filled in P5) |
| `caption_preset_id` | INTEGER | FK to `caption_preset` (table added in P4) |
| `tagger` | TEXT | model name (filled in P5) |
| `generation_meta` | JSON | raw ComfyUI workflow / A1111 parameters |
| `clip_embedding` | BLOB | CLIP/SigLIP embedding (filled in P5) |
| `created_at` | DATETIME | EXIF capture date; UTC naive |
| `imported_at` | DATETIME | import timestamp; UTC naive; indexed |
| `processed_at` | DATETIME | last full pipeline run |

Indexes: `ix_asset_content_hash` (unique), `ix_asset_created_at`.

### `asset_instance` (migration 0002)

Physical copy per person. Stage 1: one instance per asset (`person = _unknown`).

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
| `is_default` | BOOLEAN | default preset per captioner |
| `created_at` | DATETIME | UTC naive |

---

## Upcoming tables (planned)

| Table | Migration | Plan |
|---|---|---|
| `version` | 0005 | P8 |
| `face` | 0005 | P7 |
| `tag`, `asset_tag` | 0006 | P5 |
| `collection`, `collection_item`, `smart_trigger` | 0007 | P6 |
| `prompt_template` | 0008 | P9 |

> Migration `0003` is taken by P3 (reconcile `missing_at` marker) — downstream plan numbers shifted up by one.

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

Path overridable via `PHOTOFANT_CACHE_DB_PATH` env var (mirrors the pattern of `PHOTOFANT_DB_PATH`).
