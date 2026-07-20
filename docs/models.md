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

### `person` (migration 0002, erweitert 0026)

| Column | Type | Notes |
|---|---|---|
| `id` | INTEGER PK | |
| `name` | TEXT | nullable; `_unknown` for the seed row |
| `is_unknown` | BOOLEAN | `1` for the `_unknown` catch-all person |
| `group_name` | TEXT | nullable; freie Gruppen-Zuweisung (z.B. „Familie") |
| `created_at` | DATETIME | nullable; `NULL` für Bestandspersonen (kein Backfill), neue Personen setzen UTC-Zeitstempel |

Seed row: `id=1, name='_unknown', is_unknown=1` — inserted by migration 0002.

### `asset` (migration 0002)

One row per unique content-hash (canonical image).

| Column | Type | Notes |
|---|---|---|
| `id` | INTEGER PK | |
| `content_hash` | TEXT UNIQUE | SHA-256 hex; indexed |
| `source` | TEXT | `original \| sdxl \| flux \| ai_generated`; indexed |
| `width` | INTEGER | pixels |
| `height` | INTEGER | pixels |
| `file_size` | INTEGER | bytes |
| `format` | TEXT | `png \| jpeg \| webp \| …` |
| `framing` | TEXT | `close_up \| medium \| full_body \| …` (filled in P5); indexed |
| `quality_score` | REAL | (filled in P5) |
| `age` | INTEGER | from `buffalo_l` (filled in P7) |
| `caption` | TEXT | Florence-2 caption (filled in P5 Phase 3) |
| `captioner` | TEXT | captioner manifest_id, e.g. `florence-2-base` (P5 Phase 3) |
| `caption_preset_id` | INTEGER FK → `caption_preset.id` | provenance: which preset produced the caption (FK added P5 Phase 4, `fk_asset_caption_preset`) |
| `tagger` | TEXT | model name (filled in P5) |
| `generation_meta` | JSON | raw ComfyUI workflow / A1111 parameters |
| `clip_embedding` | BLOB | Image embedding of the active semantic_search model, float32 unit-norm bytes (1024-dim seit SigLIP2, P35 Phase 2; vorher CLIP 768-dim). Spaltenname bleibt inert (ADR-022). Source of truth für den Vector Index (P5 Phase 4); `deferred=True` (P32 Phase 1) — nicht Teil des Default-Selects, muss explizit geladen werden |
| `dino_embedding` | BLOB | DINOv2 visual-rerank embedding, float32 unit-norm bytes (768-dim, P37 / ADR-024). Zweiter, rein visueller Vektorraum neben `clip_embedding` — unabhängig, kann NULL sein (Asset noch nicht DINOv2-embedded → Rerank degradiert auf SigLIP2). Source of truth für `vec_asset_dino`; `deferred=True` |
| `caption_edited` | BOOLEAN | `1` = Caption wurde manuell editiert; Captioner überspringt den Asset beim nächsten Rerun (P6 Phase 3) |
| `original_id` | INTEGER FK → `asset.id` | gesetzt wenn dieses Asset ein Edit eines anderen ist — bei Review-Entscheidung „A/B ist Original" (migration 0014) |
| `created_at` | DATETIME | EXIF capture date; UTC naive |
| `imported_at` | DATETIME | import timestamp; UTC naive; indexed |
| `processed_at` | DATETIME | last full pipeline run |

Indexes: `ix_asset_content_hash` (unique), `ix_asset_created_at`, `ix_asset_original_id`
(migration 0023, P21 Phase 1 — Stapel-Query resolviert `original_id`-Ketten pro Seite),
`ix_asset_source`, `ix_asset_framing` (migration 0038 — Galerie-Filter „Quelle"/„Framing").

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
| `favourite` | BOOLEAN | mirrors physical location in `favourites/` (P5: toggled via physical move); indexed |
| `fixed_person` | BOOLEAN | manually sorted — no auto-redistribution |
| `deleted_at` | DATETIME | soft-delete; NULL = active; indexed |
| `missing_at` | DATETIME | reconcile marker (migration 0003); NULL = present; a timestamp = acknowledged-missing, hidden from the next FS↔DB scan |

Unique constraint: `(asset_id, person_id)`. Indexes: `ix_asset_instance_deleted_at`,
`ix_asset_instance_person_id` (migration 0030, P32 Phase 1 — Personen-Counts/Galerie-Filter/Namenssuche filtern über `person_id`),
`ix_asset_instance_favourite` (migration 0038 — Galerie-Filter „Favoriten").

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
| `embedding_done` | BOOLEAN | SigLIP2 embedding computed (migration 0007, set in P5 Phase 4) |
| `dino_embedding_done` | BOOLEAN | DINOv2 embedding computed (migration 0033, P37). Eigenes Flag, damit eine Bibliothek DINOv2 per Rerun-Step `dino_embedding` nachbekommt, ohne SigLIP2 neu zu rechnen |
| `classified` | BOOLEAN | `True` wenn die Klassifizierungs-Kategorien für diesen Content-Hash berechnet sind (WD14+CLIP-Fusion, P18 Phase 2); zurückgesetzt vom Rerun-Step `categories`. Spalte existiert seit Migration 0009, war bis P18 ungenutzt. |

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
| `components` | JSON | named component paths (e.g. Flux: `{"diffusion": …, "text_encoder": …, "vae": …}`); also carries an optional single-file companion for non-component models, e.g. GGUF `{"mmproj": …}` (P35/ADR-029 Vision-Naht) |
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

Unique constraint: `(asset_id, tag_id)`. Indexes: `ix_asset_tag_asset_id`,
`ix_asset_tag_tag_id` (migration 0028 — tag-filter/facet join by `tag_id`).

### `asset_caption_fts` (migration 0028)

FTS5 external-content virtual table — the searchable full-text index over `asset.caption`
for `q_mode=text` (ADR-015-Nachtrag). Rowid = `asset.id`. The canonical caption text lives
on `asset.caption`; this table only stores the token index (`content='asset',
content_rowid='id'`), kept in sync by three triggers (`asset_caption_fts_ai/_ad/_au`) that
fire on `asset` insert/delete/caption-update — no application code needs to maintain it.
Persists in `db.sqlite`. Not part of `Base.metadata` — created only by the migration, so
code that touches it degrades gracefully when the table is absent (e.g. throw-away test
DBs); see `photofant/db/text_index.py`.

| Column | Type | Notes |
|---|---|---|
| `rowid` | INTEGER | = `asset.id` |
| `caption` | TEXT | indexed only, `tokenize='unicode61 remove_diacritics 2'` |

> Query via `text_index.search_caption_asset_ids` — sanitizes free-text input into a safe
> `MATCH` query (tokens quoted + prefix-`*`'d) and returns `None` if the table is missing,
> so the caller can fall back to `Asset.caption.ilike(...)`.

Also added in migration 0028: `ix_asset_effective_date`, an expression index on
`asset (coalesce(created_at, imported_at))` mirroring the exact sort expression
`list_assets` uses for date ordering.

### `vec_asset_embedding` (migration 0007, dim 1024 seit 0032)

sqlite-vec `vec0` virtual table — the searchable image-embedding vector index (ADR-001, ADR-022). Rowid =
`asset.id`; one row per embedded asset. The canonical embedding lives on
`asset.clip_embedding` (BLOB); this table is a **rebuildable** index over those BLOBs
(`photofant/db/vector_index.py:rebuild_index`). Persists in `db.sqlite`, so it survives a
restart with no reconstruction. Maintained on import (insert) and final delete (remove);
not part of `Base.metadata` — created only by the migration, so code that touches it
degrades gracefully when the table is absent (e.g. throw-away test DBs).

| Column | Type | Notes |
|---|---|---|
| `rowid` | INTEGER | = `asset.id` |
| `embedding` | `float[1024]` | SigLIP2-Dimension (P35 Phase 2; vorher `float[768]` CLIP). `distance_metric=cosine`; cosine similarity = `1 − distance` |

> Requires the sqlite-vec loadable extension, loaded per connection via the SQLAlchemy
> `connect` event (`photofant/db/engine.py`) and inside migration 0007 (`op.get_bind()`).

### `vec_asset_dino` (migration 0033, dim 768)

sqlite-vec `vec0` virtual table — the searchable **DINOv2 visual-rerank** vector index (P37, ADR-024).
Second, independent space next to `vec_asset_embedding`: same rowid (`asset.id`), different model and
dimension, no shared index. Canonical embedding on `asset.dino_embedding` (BLOB); rebuildable over those
BLOBs via the shared parametrized core in `photofant/db/vector_index.py`. An asset may be indexed here, in
`vec_asset_embedding`, in both, or in neither — a missing row is a valid state (rerank degrades to plain
SigLIP2). Maintained on embed (upsert) and final delete (remove, both indexes).

| Column | Type | Notes |
|---|---|---|
| `rowid` | INTEGER | = `asset.id` |
| `embedding` | `float[768]` | DINOv2-with-registers-base Dimension. `distance_metric=cosine`; cosine similarity = `1 − distance` |

> Requires the sqlite-vec loadable extension (same loading path as `vec_asset_embedding`; migration 0033
> loads it before creating **and** before dropping the table — a vec0 table can't be dropped without the module).

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
| `kind` | TEXT | `album \| smart_album \| training_set` |
| `match_mode` | TEXT | smart_album only: `any` (OR) \| `all` (AND) |
| `settings` | JSON | training_set only (P10 Phase 2): `{ trigger_word, prefix, suffix, split_ratio }`, all nullable; NULL otherwise |

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

### `review_item` (migration 0014, erweitert in 0017/0025/0027 — ADR-007)

Zwei Review-Typen teilen sich die Tabelle: offene Duplikat-Paare (`dupe_candidate`) und Gesichts-Zuordnungsvorschläge aus dem Clustering (`face_suggestion`).

| Column | Type | Notes |
|---|---|---|
| `id` | INTEGER PK | |
| `type` | TEXT | `dupe_candidate` · `face_suggestion` |
| `asset_a_id` | INTEGER FK → `asset.id` | dupe_candidate: kleinere ID. face_suggestion: gleiche Asset-ID wie `asset_b_id` (Hack, siehe unten) |
| `asset_b_id` | INTEGER FK → `asset.id` | dupe_candidate: größere ID. face_suggestion: = `asset_a_id` |
| `clip_distance` | REAL | nullable; Cosine-Distance (0.0–1.0) — bei `dupe_candidate` die einzige Distanz-Metrik (P33/ADR-018). Spaltenname bleibt inert: seit P37 Phase 4 (ADR-024) ist der Wert eine DINOv2-Distanz, nicht mehr CLIP/SigLIP2. `NULL` bleibt nur bei resolved Alt-Zeilen aus der Vor-ADR-018-Aera möglich |
| `created_at` | DATETIME | UTC naive; nicht null |
| `resolved_at` | DATETIME | nullable; gesetzt bei Entscheidung |
| `resolution` | TEXT | nullable: `a_is_original` · `b_is_original` · `delete_a` · `delete_b` · `dismiss` (dupe_candidate); `confirmed` · `rejected` · `reassigned:<id>` (face_suggestion) |
| `face_id` | INTEGER | nullable; nur bei `face_suggestion` gesetzt, `NULL` bei `dupe_candidate` |
| `suggested_person_id` | INTEGER | nullable; nur bei `face_suggestion` |
| `score` | REAL | nullable; Match-Score (0.0–1.0), nur bei `face_suggestion` |

Zwei partielle Unique-Indizes (migration 0027 — ersetzt den ursprünglichen, zu breiten `uq_review_item_pair`-Constraint):
- `uq_review_item_pair` auf `(type, asset_a_id, asset_b_id)` **WHERE `face_id IS NULL`** — kein Doppeleintrag pro Duplikat-Paar.
- `uq_review_item_face_pending` auf `(face_id)` **WHERE `type = 'face_suggestion' AND resolved_at IS NULL`** — höchstens ein offener Vorschlag pro Gesicht gleichzeitig, aber nach Bestätigen/Ablehnen darf ein neuer entstehen (z.B. nach erneutem Clustering-Lauf).

Grund für die Aufteilung: `face_suggestion`-Zeilen setzen `asset_a_id == asset_b_id` (kein "Paar", nur ein Gesicht) — ein Foto mit mehreren Gesichtern, die alle zur Review anstehen, konnte sonst nur die erste Zeile einfügen (UNIQUE-Verletzung auf `(type, asset_a_id, asset_b_id)` ab dem zweiten Gesicht desselben Fotos).

Zusätzlich `ix_review_item_type_resolved_at` auf `(type, resolved_at)` (migration 0038) — die
Review-Queue-Listen filtern durchgängig auf beide Spalten zusammen; die beiden partiellen
Unique-Indizes oben sind auf andere Bedingungen gemünzt und bedienen diesen Zugriff nicht.

Flow Duplikate (ADR-018; DINOv2 seit P37 Phase 4, ADR-024): Embedding-Job berechnet `dino_embedding` → Post-Embedding-Check via sqlite-vec-Suche auf `vec_asset_dino` (Cosine-Distance ≤ `dupe_dino_threshold`) legt bei Treffer ein `review_item` an → User entscheidet im Review-Tab. Läuft nur, wenn ein DINOv2-Modell aktiv ist (kein Fallback auf SigLIP2 — Duplikat-Erkennung ist Primärsignal, nicht Rerank). `dupe_clip_threshold` bleibt als Settings-Key inert für Rollback.

Flow Gesichts-Vorschläge: Clustering/inkrementelles Matching (`photofant/clustering/engine.py`, `photofant/jobs/clustering_job.py`) legt für ein Gesicht mit `band == "review"` eine Zeile an → User entscheidet in der Review-Queue (`photofant/api/review_queue.py`: confirm/reject/reassign).

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
| `embedding` | BLOB | ArcFace 512-d float32, L2-normiert; `deferred=True` (P32 Phase 1) — nicht Teil des Default-Selects, muss explizit geladen werden; Basis für Face-Crop-Dedupe (Cosine, ADR-018) |
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
| `type` | TEXT | `crop \| rotate \| mirror \| pad \| rembg \| convert \| smart_crop \| import \| edit \| comfyui` (aktiv); historisch: `upscale \| flux_edit \| inpaint` (P9, entfernt) |
| `parent_id` | INTEGER FK → `version.id` | Edit eines Edits → Kette; NULL = erste Version |
| `path` | TEXT | Datei in `personX/edits/`, nicht null |
| `is_current` | BOOLEAN | `0` default; genau eine Version pro instance/face ist `1` |
| `params` | JSON | `{ steps: [{op, params}], width, height }` |
| `created_at` | DATETIME | UTC naive |

Indexes: `ix_version_instance_id`, `ix_version_face_id`. Check constraint: `ck_version_xor`.

**Galerie-Stapel (P21, ADR-012):** Jede `version`-Zeile erscheint als eigener,
gleichberechtigter Galerie-Eintrag (kein Kollabieren) — `stack_size`/`stack_group_id`
werden zur Query-Zeit berechnet (Original + seine `version`-Zeilen + seine
`original_id`-Kind-Assets), keine eigene Spalte. Bewusster Kompromiss: `original_id`-
Ketten (ComfyUI-Edit-eines-Edits) werden für die Größen-Zählung nur single-hop
gezählt, die Gruppen-Identität selbst löst bounded-rekursiv (Tiefe 5) auf.

---

### `prompt_template` (migration 0020)

| Column | Type | Notes |
|---|---|---|
| `id` | INTEGER PK | |
| `name` | TEXT | nicht null; Anzeigename |
| `prompt` | TEXT | nicht null; `{person}` als Platzhalter |
| `params` | JSON | `{ strength?, steps?, guidance?, seed? }` — nullable |
| `created_at` | DATETIME | UTC naive |

Seed-Daten (migration 0020): 'Portrait verbessern', 'Anime-Stil', 'Hintergrund entfernen'.

### `classification_category` (migration 0029, P18 Phase 1)

Frei definierbare Klassifizierungs-Kategorie (z.B. "Medium", "Stil", "Franchise").

| Column | Type | Notes |
|---|---|---|
| `id` | INTEGER PK | |
| `name` | TEXT UNIQUE | nicht null; Anzeigename |
| `mode` | TEXT | `single` (genau eine Hauptklasse) \| `multi` (mehrere Klassen); nicht null |
| `position` | INTEGER | Sortierung in Einstellungen-Tab + Galerie-Filter |
| `enabled` | BOOLEAN | Default `1` |
| `builtin` | BOOLEAN | Default `0`; `1` = aus dem Konzept-Seed-Katalog (löschbar, nur zur Kennzeichnung) |
| `min_confidence` | FLOAT | nullable; überschreibt pro Kategorie die globale `classification.min_confidence` (nur für `single`-Modus relevant) |

Seed-Katalog (migration 0029, `builtin=1`): Medium, Stil, Realismus, Motiv, Szene,
Eigenschaften, Technik, Franchise, Charakter, Künstler, AI-Modell — siehe
`photofant/classification/seed.py:SEED_CATALOG`.

### `classification_label` (migration 0029, P18 Phase 1)

Eine wählbare Klasse innerhalb einer Kategorie (z.B. "Anime" in "Stil").

| Column | Type | Notes |
|---|---|---|
| `id` | INTEGER PK | |
| `category_id` | INTEGER FK → `classification_category.id` ON DELETE CASCADE | indexed (`ix_classification_label_category_id`) |
| `name` | TEXT | nicht null |
| `position` | INTEGER | Sortierung innerhalb der Kategorie |
| `clip_prompts` | JSON | nullable; `list[str]` eigene CLIP-Textprompts — leer/NULL → Fallback-Template aus `settings.json` (`classification.clip_prompt_template`) |
| `wd14_tags` | JSON | nullable; `list[str]` WD14-Tag-Namen, deren gespeicherter Score dieses Label speist |

Unique constraint: `(category_id, name)` (`uq_classification_label_category_name`).

### `asset_classification` (migration 0029, P18 Phase 1)

Ergebnis der Fusion — eine Zeile pro (Asset, zugewiesenem Label).

| Column | Type | Notes |
|---|---|---|
| `asset_id` | INTEGER FK → `asset.id` | PK-Teil; indexed (`ix_asset_classification_asset_id`) |
| `label_id` | INTEGER FK → `classification_label.id` ON DELETE CASCADE | PK-Teil; indexed (`ix_asset_classification_label_id`, migration 0038 — PK-Reihenfolge `(asset_id, label_id)` deckt Einzel-Filter auf `label_id` nicht) |
| `category_id` | INTEGER FK → `classification_category.id` | denormalisiert für Filter/Facets; indexed (`ix_asset_classification_category_id`) |
| `confidence` | FLOAT | nicht null; fusionierter Score |
| `source` | TEXT | `clip` \| `wd14` \| `fused` — welche(s) Signal(e) den Score getragen haben |

PK: `(asset_id, label_id)`. **Cascade-Deletes sind hier explizit im Code** (`api/classification.py`,
`_delete_category_cascade`/`_delete_label_cascade`) — SQLite läuft projektweit ohne
`PRAGMA foreign_keys=ON`, die deklarierten `ON DELETE CASCADE` feuern also nicht von selbst.

**Berechnung:** `photofant/classification/engine.py:classify_asset()` liest ausschließlich
bereits gespeicherte Signale (`asset.clip_embedding`, `asset_tag.score`) — kein Modell-Neulauf,
kein Bild-I/O. Pro Kategorie wird je Label ein CLIP-Softmax-Score und/oder ein WD14-Score
gewichtet fusioniert (`classification.clip_weight`/`wd14_weight` in `settings.json`); `single`
wählt die Klasse mit dem höchsten Score über `min_confidence`, `multi` alle Klassen über
`classification.multi_min_confidence`. Persistiert vom Job `jobs/classification_job.py`
(ersetzt bei jedem Lauf atomar alle Zeilen des Assets), getriggert automatisch nach
Tagging+Embedding (`jobs/classification_pipeline.py`) oder manuell über den Rerun-Step
`categories`.

### ~~`comfyui_workflow`~~ (migration 0019 → **dropped in 0022**)

Tabelle wurde in P16 Phase 2 entfernt. Workflows sind jetzt Dateien in `.photofant/workflows/`,
keine DB-Einträge mehr. Migration 0022 dropped die Tabelle; Model `ComfyUIWorkflow` aus `models.py` entfernt.

### `knowledge_entities` / `knowledge_relationships` / `knowledge_sources` / `knowledge_media_links` (migration 0034, P22 Phase 2)

Reiner Cache über der Markdown-Wissensbasis (`photofant/knowledge/vault.py`, ADR-025) —
jede Zeile ist aus dem Vault identisch neu aufbaubar, geschrieben ausschließlich über
`knowledge/repository.py::EntityRepository.upsert_from_vault`. Kein Feld ohne
Markdown-Entsprechung (Kontrakt, siehe `docs/planning/2026-07-01_p22-knowledge-engine/README.md`).

**`knowledge_entities`**

| Column | Type | Notes |
|---|---|---|
| `id` | TEXT PK | Entity-`id` aus dem Vault (`<type>/<slug>`), keine Autoincrement-ID |
| `type` | TEXT | Entity-Typ (domänenabhängig, z.B. `actor`); indexed |
| `title` | TEXT | Anzeigename |
| `domain` | TEXT | Domänenname (z.B. `Movies`); indexed |
| `owner` | TEXT | `Owner`-Wert (`user\|manual\|web\|inferred`) |
| `confidence` | REAL | 0.0–1.0 |
| `status` | TEXT | frei, kann leer sein |
| `aliases` | JSON | Liste von Alias-Strings; Suche via `cast(aliases, Text).like(...)` (kein FTS, laut Kontrakt optional) |

**`knowledge_relationships`** — `id` PK, `entity_id` FK → `knowledge_entities.id` (Quelle, indexed), `type` TEXT, `target` TEXT (Ziel-Entity-`id`, indexed, **keine FK** — Ziel kann vor/nach der Beziehung angelegt werden).

**`knowledge_sources`** — `id` PK, `entity_id` FK → `knowledge_entities.id` (indexed), `source` TEXT (freier String, z.B. URL).

**`knowledge_media_links`** — `id` PK, `entity_id` FK → `knowledge_entities.id` (indexed), `kind` TEXT (`person\|asset`), `target_id` INTEGER (`person.id`/`asset.id` je nach `kind`, **keine FK** — Zieltabelle variiert, gleiches Muster wie `review_item.face_id`). `UNIQUE(entity_id, kind, target_id)`.

**Cascade-Deletes sind explizit im Code** (`knowledge/repository.py::EntityRepository.delete`) —
SQLite läuft projektweit ohne `PRAGMA foreign_keys=ON`, die deklarierten FKs erzwingen also
nichts von selbst (gleiches Muster wie `classification_label`/`asset_classification` oben).

### `knowledge_tasks` (migration 0035, P23 Phase 1)

Aufgaben-Queue für „hier fehlt Wissen" — reiner Arbeitszustand, kein Vault-Wissen (Gegenstück
zu den `knowledge_*`-Cache-Tabellen oben, die den Markdown-Vault spiegeln). Geschrieben
ausschließlich über `knowledge/tasks.py::TaskService`.

| Column | Type | Notes |
|---|---|---|
| `id` | INTEGER PK | autoincrement |
| `kind` | TEXT | `new_person\|missing_entity\|confirm_relationship\|review_recommendation` (indexed) |
| `status` | TEXT | `open\|resolved\|dismissed`, Default `open` (indexed); Übergang nur `open` → `resolved`/`dismissed`, kein zweiter Wechsel |
| `context` | JSON | frei geformt (z.B. `{"ref": "actors/robert-downey-jr"}`); Dedup über `kind` + exakte `context`-Gleichheit unter **offenen** Aufgaben |
| `created_at` | DATETIME | gesetzt bei Anlage |
| `resolved_at` | DATETIME | NULL solange offen; gesetzt bei `resolve` **und** `dismiss` (ein Feld für „wann geschlossen", keine zwei) |

`KnowledgeLookupJob` (`jobs/knowledge_lookup_job.py`) legt bei fehlender Entity (`KnowledgeService.find_entity`
liefert `None`) genau eine Aufgabe an; ein mehrdeutiger Alias-Treffer (`AmbiguousEntityError`) zählt als
gefunden, keine Aufgabe. Automatischer Trigger aus Ereignissen erst ab P24 — hier nur manuell über
`POST /api/knowledge/lookup` auslösbar.

### `recommendation_cache` (migration 0036, P26 Phase 1)

Ergebnis-Cache der Empfehlungen „Bild → Bild" — jederzeit aus CLIP-Nachbarn + Wissensgraph
neu berechenbar (`jobs/recommendation_job.py`), keine Wahrheit. Geschrieben ausschließlich
über `store_recommendations` (voller Ersatz je Quell-Asset, kein Merge).

| Column | Type | Notes |
|---|---|---|
| `id` | INTEGER PK | autoincrement |
| `source_asset_id` | INTEGER FK → `asset.id` | das Bild, zu dem empfohlen wird (indexed: `ix_recommendation_source`) |
| `recommended_asset_id` | INTEGER FK → `asset.id` | das empfohlene Bild |
| `score` | FLOAT | gewichtete Summe der Signale; Default-Gewichte summieren zu 1.0 → Score in [0, 1] |
| `reasons` | JSON | Begründungskette `[{signal, detail, weight}]` (`signal` ∈ `same_person\|same_role\|same_film\|clip`); geteilte Explainability-Payload mit P25 und P26 Phase 3 |
| `computed_at` | DATETIME | Zeitpunkt der Berechnung |

`UNIQUE(source_asset_id, recommended_asset_id)`. Kein DB-seitiges Cascade (SQLite-FK-Enforcement
aus) — verwaiste Zeilen nach Asset-Löschung sind unschädlich, die Lese-Route (`api/recommendations.py`)
filtert aktiv gegen `asset_instance.deleted_at`.

## Upcoming tables (planned)

*(keine offenen Tabellen)*

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
