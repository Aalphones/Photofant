# Photofant — Konzept

> **Arbeitstitel:** Photofant · *„vergisst nie"* — lokale, private Bildsammlung, vollständig durchsuchbar.

Komfortable Verwaltung lokal gehaltener Bildsammlungen mit Google-Fotos-Vorbild. Fokus auf lokale Durchsuchbarkeit, Organisation, Klassifizierung und Bearbeitung. Verarbeitung und Datenhaltung rein lokal über das Dateisystem. Privat, lokal, keine Drittsysteme, keine Internetdienste zur Laufzeit.

---

## 1. Leitprinzipien

1. **Lokal & privat:** Zur Laufzeit findet kein Netzwerkverkehr statt. Modelle werden einmalig über eine Konfigurationsseite bezogen, danach läuft alles offline (inkl. `HF_HUB_OFFLINE=1` / `TRANSFORMERS_OFFLINE=1`, falls torch-basierte Modelle aktiv sind).
2. **Single-User, keine Authentifizierung.**
3. **Saubere Person-Ordner, alle Informationen in der DB:** Bilder werden pro Person als echte Kopie abgelegt. Es gibt **keine Sidecar-Dateien** — sämtliche Metadaten, Tags, Captions, Klassifizierungen und Beziehungen liegen ausschließlich in der Datenbank. Die Person-Ordner enthalten **nur Bilddateien** der jeweiligen Person, nichts anderes. Das Risiko des Datenverlusts bei Verlust der DB wird bewusst akzeptiert.
4. **Einmalige Verarbeitung:** Schwere Verarbeitung (Face-Extraction, Recognition, Tagging, Caption) erfolgt genau einmal pro Quellbild, identifiziert über einen Content-Hash. Die DB ist Index und alleinige Ablage aller Informationen.
5. **Modellunabhängig & konfigurierbar:** Keine Modelle im Repository. Modelle werden über eine Konfigurationsseite bezogen — per In-App-Download **oder durch Einbinden bereits vorhandener Dateien** (kein Doppel-Download) — in mehreren Varianten (fp16/fp8/GGUF) je nach GPU. Der **Modell-Ordner ist frei wählbar**. Features bleiben deaktiviert, bis das nötige Modell konfiguriert ist.

---

## 2. Architektur (High-Level)

```
┌────────────────────────────────────────────────────────────┐
│  Frontend (Angular + Tailwind + NgRx)                        │
│  Galerie · Filter/Suche · Editor · Trainingssets · Settings  │
└───────────────▲───────────────────────────┬─────────────────┘
                │ REST / SSE (Fortschritt)   │
┌───────────────┴───────────────────────────▼─────────────────┐
│  Backend (Python · FastAPI)                                  │
│  ┌──────────────┐  ┌───────────────┐  ┌──────────────────┐   │
│  │ API-Layer    │  │ Job-Queue     │  │ Inferenz-Layer   │   │
│  │ (Endpoints)  │  │ (in-process,  │  │ ONNX Runtime     │   │
│  │              │  │  idempotent)  │  │ (Core)           │   │
│  └──────┬───────┘  └──────┬────────┘  │ torch/diffusers  │   │
│         │                 │           │ o. ComfyUI       │   │
│         │                 │           │ (generativ, opt.)│   │
│  ┌──────▼─────────────────▼───────────┴──────────────────┐   │
│  │ SQLite (Index + Zusatzinfos) · Alembic (Migrationen)  │   │
│  └───────────────────────┬──────────────────────────────┘   │
└──────────────────────────┼──────────────────────────────────┘
                ┌──────────▼───────────┐
                │  Dateisystem         │
                │  Person-Ordner:      │
                │  photos/favourites/  │
                │  faces/edits/        │
                │  + DBs (Meta+Thumbs) │
                └──────────────────────┘
```

---

## 3. Erweiterter Techstack

| Ebene | Technologie | Zweck |
|---|---|---|
| Frontend-Framework | Angular | SPA, Routing, Komponenten |
| Styling | Tailwind CSS | Utility-First-Styling |
| State Management | NgRx (Store, Effects, Entity) | zentraler State, async Flows |
| UI-Performance | Server-seitige Pagination | seitenweises Thumbnail-Grid (kein Virtual Scroll) |
| Backend-Framework | FastAPI (Python) | REST-API, async, SSE/WebSocket |
| ASGI-Server | Uvicorn | Backend-Runtime |
| Datenbank | SQLite | lokaler Index, Zusatzinfos |
| Migrationen | Alembic | versionierte Schema-Änderungen |
| Vektorsuche | `sqlite-vec` (oder FAISS) | Face-Matches **und** semantische Bild-Suche (CLIP/SigLIP) |
| Core-Inferenz | ONNX Runtime | Face, Tags, Caption (CPU/GPU) |
| Generativ-Inferenz | torch + diffusers **oder** ComfyUI-Backend | Edit (img2img), Upscale |
| Bildverarbeitung | Pillow / OpenCV | I/O, Crop, Rotate, Mirror, Konvertierung, pHash |
| Clustering | HDBSCAN / DBSCAN | automatische Personen-Gruppierung |
| Paketverwaltung | `uv` / `pip` mit Lockfile | reproduzierbare, gepinnte Umgebung |
| Modell-Binaries | Git LFS / externer Download | keine Modelle im Plain-Git |

---

## 4. Datenhaltung & Verzeichnisstruktur

### 4.1 Prinzip

- **Quellbild → Content-Hash (SHA-256).** Über den Hash wird erkannt, ob ein Bild bereits verarbeitet wurde. Schwere Verarbeitung läuft genau einmal.
- **Echte Kopien pro Person.** Ist eine Person auf einem Bild, bekommt sie eine echte Kopie in ihrem Person-Ordner. Mehrere Personen → mehrere Kopien (bewusst).
- **Keine Sidecars — DB ist alleinige Metadaten-Wahrheit.** Es liegen keinerlei Metadaten-Dateien im Dateisystem. Tags, Captions, Klassifizierung, Quelle, Beziehungen, Embeddings und Versionen leben ausschließlich in der DB. **Datenverlust-Risiko bei Verlust der DB wird bewusst akzeptiert.**
- **Bilddaten bleiben im Dateisystem, sortiert pro Person in Unterordnern:** `photos`, `favourites`, `faces`, `edits`. Jeder Person-Ordner enthält ausschließlich Bilddateien dieser Person (keine Metadaten-Dateien).
- **Cache-DB für flüchtige Daten.** Eine separate `thumbnails.sqlite` hält die flüchtigen, jederzeit regenerierbaren Daten als BLOBs: **Thumbnails** (echte verkleinerte Duplikate) **und die versionierte Edit-Step-History** (für Rollback). Diese Daten haben im Dateisystem **nichts verloren**.
- **Edits ins Dateisystem nur durch aktives Speichern.** In `personX/edits/` landet ein Edit erst, wenn der Nutzer ihn bewusst speichert (überschreiben oder als neue Kopie). Davor existiert er nur als flüchtige History in der Cache-DB. Details siehe Abschnitt 8.2.
- **Interner Store nur für DBs & Verwaltung.** Im app-internen `.photofant/` liegen ausschließlich die beiden SQLite-DBs, Papierkorb und Backups.
- **Aktive Verschiebungen statt Verknüpfungen.** Favoriten und manuelle Korrekturen verschieben die Bilddatei physisch (kein Symlink/keine Referenz).

### 4.2 Verzeichnisbaum

```
Data/
├── _unknown/                 # noch nicht zugeordnete Bilder
│   ├── photos/
│   ├── favourites/
│   ├── faces/
│   └── edits/
├── personA/                  # nur Bilddateien von personA, in Unterordnern
│   ├── photos/               # Original-Fotos
│   ├── favourites/           # favorisierte Bilder (physisch hierher verschoben)
│   ├── faces/                # Face-Crops (mit Padding) + Face-Originale
│   └── edits/                # gespeicherte Edit-/Upscale-Versionen
├── personB/
│   └── …
└── .photofant/               # app-intern (nicht für den Nutzer)
    ├── db.sqlite             # Metadaten, Beziehungen, Embeddings, Versionen, Pfade
    ├── thumbnails.sqlite     # flüchtige Daten: Thumbnail-BLOBs + Edit-Step-History (versioniert)
    ├── trash/                # Papierkorb (Soft-Delete mit Aufbewahrung)
    └── backups/              # exportierte DB-Snapshots
```

> Die DB speichert **nur** Thumbnails als Bilddaten (BLOBs). Alle anderen Bilddateien — Fotos, Favoriten, Faces, Edits — liegen im Dateisystem in den jeweiligen Person-Unterordnern; die DB hält dazu lediglich Pfade und Metadaten.

### 4.3 Favoriten & manuelle Korrektur (aktive Moves)

- **Favorit setzen:** Bilddatei wird aus `personX/photos/` nach `personX/favourites/` **verschoben**. Wird der Favorit entfernt, wandert sie zurück. Keine Verknüpfung.
- **Manuelle Korrektur:** Bei falscher Personen-Zuordnung wird die Bilddatei aktiv in den richtigen Person-Ordner verschoben; zugehörige Face-Crops und Edits ziehen in dessen `faces`/`edits`-Unterordner mit. Ziel: jeder Person-Ordner enthält tatsächlich rein nur Bilder dieser Person.
- Die DB führt zu jeder Datei den aktuellen Pfad nach und wird bei jedem Move aktualisiert.

---

## 5. Datenmodell / DB-Schema

Kernidee: **`asset`** ist das kanonische Quellbild (eine Zeile pro Content-Hash). Semantische Daten (Tags, Caption, Quelle) hängen am `asset` und werden einmal berechnet. **`asset_instance`** ist die physische Kopie pro Person. **`version`** bildet die Bearbeitungs-Historie ab und kann sowohl an einer Instanz als auch an einem **`face`** hängen. Ein `face` ist das (pro Person) extrahierte Gesicht mit Provenienz — kann aber auch **eigenständiges Original** sein (manuell direkt einsortiert, ohne zugrundeliegendes Foto).

```sql
-- Kanonisches Quellbild (einmal pro Hash)
CREATE TABLE asset (
    id            INTEGER PRIMARY KEY,
    content_hash  TEXT UNIQUE NOT NULL,
    source        TEXT,              -- original | sdxl | flux | …
    width         INTEGER,
    height        INTEGER,
    file_size     INTEGER,
    format        TEXT,              -- png | jpeg | …
    framing       TEXT,              -- close_up | medium | full_body | …
    quality_score REAL,
    age           INTEGER,           -- aus buffalo_l
    caption       TEXT,
    captioner     TEXT,              -- genutztes Caption-Modell
    caption_preset_id INTEGER REFERENCES caption_preset(id), -- mit welchem Preset erzeugt (Provenienz)
    tagger        TEXT,              -- genutztes Tagger-Modell
    generation_meta JSON,            -- ausgelesene PNG/EXIF-Workflow-Daten
    clip_embedding BLOB,             -- CLIP/SigLIP-Embedding für semantische Suche
    created_at    DATETIME,          -- EXIF-Aufnahmedatum, falls vorhanden
    imported_at   DATETIME,
    processed_at  DATETIME
);

-- Physische Kopie pro Person
CREATE TABLE asset_instance (
    id            INTEGER PRIMARY KEY,
    asset_id      INTEGER REFERENCES asset(id),
    person_id     INTEGER REFERENCES person(id),
    path          TEXT NOT NULL,     -- aktueller Pfad der Bilddatei (folgt Moves)
    favourite     BOOLEAN DEFAULT 0, -- spiegelt physische Lage im favourites/-Ordner
    fixed_person  BOOLEAN DEFAULT 0, -- vom Nutzer aktiv einsortiert → keine Auto-Umverteilung
    deleted_at    DATETIME,          -- Soft-Delete: gesetzt = im Papierkorb
    UNIQUE(asset_id, person_id)
);

CREATE TABLE person (
    id          INTEGER PRIMARY KEY,
    name        TEXT,
    is_unknown  BOOLEAN DEFAULT 0
);

-- Versionen (Bearbeitungshistorie). Hängt an einer Instanz ODER einem Face.
CREATE TABLE version (
    id            INTEGER PRIMARY KEY,
    instance_id   INTEGER REFERENCES asset_instance(id),  -- gesetzt: Edit eines Fotos
    face_id       INTEGER REFERENCES face(id),            -- gesetzt: Edit eines Faces
    type          TEXT,              -- original | crop | rotate | mirror | upscale | flux_edit | inpaint | rembg | convert
    parent_id     INTEGER REFERENCES version(id),         -- Edit eines Edits → Kette
    path          TEXT NOT NULL,     -- Datei in personX/edits/
    is_current    BOOLEAN DEFAULT 0,
    params        JSON,              -- z.B. Crop-Box, Winkel, Prompt, Strength, Seed
    created_at    DATETIME
    -- genau eines von instance_id / face_id ist gesetzt
);

-- Faces (pro Person, mit Provenienz). Kann auch eigenständiges Original sein.
CREATE TABLE face (
    id                INTEGER PRIMARY KEY,
    asset_id          INTEGER REFERENCES asset(id),       -- NULL = eigenständiges Face ohne Original
    person_id         INTEGER REFERENCES person(id),
    source_version_id INTEGER REFERENCES version(id),     -- NULL bei manuellem Original
    crop_path         TEXT NOT NULL,                       -- Datei in personX/faces/
    bbox              JSON,
    padding           INTEGER,
    embedding         BLOB,          -- für Recognition / Top-Matches
    phash             TEXT,          -- für Crop-Dedupe
    origin            TEXT,          -- derived | manual_original
    origin_type       TEXT,          -- original | upscale | flux_edit
    is_upscaled       BOOLEAN DEFAULT 0,
    resolution        INTEGER,
    created_at        DATETIME
);

-- Tags (automatisch + manuell), inkl. Alias/Merge
CREATE TABLE tag (
    id        INTEGER PRIMARY KEY,
    name      TEXT UNIQUE,
    kind      TEXT,                  -- auto | manual | character | series | …
    alias_of  INTEGER REFERENCES tag(id)  -- gesetzt = Alias/gemergt auf Ziel-Tag
);
CREATE TABLE asset_tag (
    asset_id INTEGER REFERENCES asset(id),
    tag_id   INTEGER REFERENCES tag(id),
    PRIMARY KEY (asset_id, tag_id)
);

-- Alben / Collections / Trainingssets / Smart-Alben
CREATE TABLE collection (
    id           INTEGER PRIMARY KEY,
    name         TEXT,
    kind         TEXT,               -- album | training_set | smart_album
    match_mode   TEXT,               -- nur smart_album: any (ODER) | all (UND)
    settings     JSON                -- nur training_set: trigger_word, prefix, suffix, split …
);

-- Trigger eines Smart-Albums (automatische Befüllung)
CREATE TABLE smart_trigger (
    id            INTEGER PRIMARY KEY,
    collection_id INTEGER REFERENCES collection(id),
    type          TEXT,              -- person | tag | caption
    person_id     INTEGER REFERENCES person(id),  -- bei type=person
    tag_id        INTEGER REFERENCES tag(id),      -- bei type=tag
    phrase        TEXT,              -- bei type=caption (Wort/Phrase)
    negate        BOOLEAN DEFAULT 0  -- optional: Ausschluss statt Einschluss
);

CREATE TABLE collection_item (
    collection_id INTEGER REFERENCES collection(id),
    asset_id      INTEGER REFERENCES asset(id),
    source        TEXT DEFAULT 'manual', -- manual | smart (automatisch durch Trigger)
    caption_override TEXT,           -- für Trainingssets
    PRIMARY KEY (collection_id, asset_id)
);

-- Prompt-Templates (Flux2-Edits)
CREATE TABLE prompt_template (
    id      INTEGER PRIMARY KEY,
    name    TEXT,
    prompt  TEXT,
    params  JSON                     -- strength, steps, guidance, seed
);

-- Modell-Registry (Konfiguration der Modelle/Varianten)
CREATE TABLE model_registry (
    id        INTEGER PRIMARY KEY,
    role      TEXT,                  -- face | tagger | captioner | upscale | edit
    name      TEXT,
    variant   TEXT,                  -- fp16 | fp8 | gguf-q4 | …
    format    TEXT,                  -- onnx | safetensors | gguf
    path      TEXT,                  -- Einzeldatei-Modell ODER Ordner-Modell (diffusers/Bundle); NULL bei reinen Komponenten-Modellen
    components JSON,                  -- benannte, EINZELN gewählte Komponentenpfade (z.B. Flux: {"diffusion": …, "text_encoder": …, "vae": …}) — dürfen an verschiedenen Orten liegen
    sha256    TEXT,                  -- managed: gegen Manifest geprüft · in-place: nur informativ
    managed   BOOLEAN DEFAULT 1,     -- 1 = von App im Modell-Ordner verwaltet · 0 = externe In-Place-Referenz (nicht anfassen)
    caption_mode TEXT,               -- nur Captioner: task_token | instruct | instruct_guided (s. 12.6)
    capabilities JSON,               -- deklarativer UI-Descriptor: welche Settings das Modell anbietet
    enabled   BOOLEAN DEFAULT 0,
    is_default BOOLEAN DEFAULT 0
);

-- App-weite Konfiguration (Key/Value) — u.a. frei wählbarer Default-Download-Ordner
CREATE TABLE app_config (
    key       TEXT PRIMARY KEY,      -- z.B. "models_dir" (Default-Download-Ziel)
    value     TEXT
);

-- Benannte, wiederverwendbare Captioner-Konfigurationen (s. 12.6)
CREATE TABLE caption_preset (
    id         INTEGER PRIMARY KEY,
    name       TEXT NOT NULL,        -- "Natürliche Sprache", "Danbooru-Tags", …
    model_id   INTEGER REFERENCES model_registry(id),  -- NULL = modell-übergreifend
    config     JSON NOT NULL,        -- modus-spezifisch: Task-Token / System-Prompt / Bausteine + Sampling
    is_default BOOLEAN DEFAULT 0,    -- Default-Preset je Captioner
    created_at DATETIME
);

-- Verarbeitungs-Ledger (Once-Only-Garantie)
CREATE TABLE processing_ledger (
    content_hash TEXT PRIMARY KEY,
    faces_done   BOOLEAN DEFAULT 0,
    tags_done    BOOLEAN DEFAULT 0,
    caption_done BOOLEAN DEFAULT 0,
    classified   BOOLEAN DEFAULT 0
);
```

**Cache-DB (`thumbnails.sqlite`) — flüchtige, regenerierbare Daten:**

```sql
-- Thumbnails (echte verkleinerte Duplikate)
CREATE TABLE thumbnail (
    target_kind TEXT,                  -- asset | face | edit
    target_id   INTEGER,
    size        TEXT,                   -- z.B. 256 | 512
    blob        BLOB,
    PRIMARY KEY (target_kind, target_id, size)
);

-- Versionierte Edit-Step-History (für Rollback) — bewusst NICHT im Dateisystem
CREATE TABLE edit_step (
    id          INTEGER PRIMARY KEY,
    session_key TEXT,                   -- referenziert das bearbeitete Foto/Face/Edit
    seq         INTEGER,                -- Schrittnummer in der Session
    op          TEXT,                   -- crop | rotate | flux_edit | upscale | …
    params      JSON,
    preview     BLOB,                   -- Vorschau-Thumbnail dieses Schritts
    created_at  DATETIME
);
```

---

## 6. Verarbeitungs-Pipeline

### 6.1 Import-Fluss

1. Bild einlesen, **Content-Hash** berechnen.
2. Im `processing_ledger` prüfen, ob der Hash bereits verarbeitet ist → wenn ja, nur Personen-Zuordnung/Kopie ergänzen, keine erneute Schwerverarbeitung.
3. **Metadaten lesen** (EXIF, PNG-Chunks): Dimensionen, Aufnahmedatum, Generierungs-Workflow → daraus `source` (Original/SDXL/Flux) ableiten. Kein Modell nötig.
4. **Framing** aus Face-BBox-zu-Bild-Verhältnis bestimmen (Heuristik). **Qualität** aus Auflösung, Face-Größe, Blur (Laplacian-Varianz) messen.
5. **Face Detection** (`buffalo_l`): Gesichter mit Padding extrahieren.
6. **Recognition/Zuordnung:** Embeddings berechnen, gegen bestehende Personen-Cluster matchen; nicht zuordenbar → `_unknown`.
7. **Tagging** (WD14) + **Caption** (Florence-2) + **CLIP/SigLIP-Embedding** (für semantische Suche): Ergebnisse speichern.
8. **Kopien anlegen:** pro erkannter Person eine echte Kopie in `personX/photos/` (nur die Bilddatei, kein Sidecar); Face-Crop in `personX/faces/`.
9. **DB + Ledger** aktualisieren.

Die Schritte 5–7 laufen als **idempotente Jobs in einer In-Process-Queue** (kein Celery/Redis nötig), gekoppelt an den Content-Hash. Fortschritt wird per SSE/WebSocket ans Frontend gestreamt.

### 6.1a Manuell eingeschobene Bilder (Filesystem-Drop)

Es ist möglich, neue Bilder direkt in einen bestehenden Person-Ordner zu schieben. Das System erkennt Dateien ohne DB-Eintrag und stellt deren Verarbeitung in die Queue. Dabei gilt:

- **Person ist fix:** Die Person des Ziel-Ordners ist verbindlich (`fixed_person = true`) — das Bild wird **nicht** automatisch zu einer anderen Person verschoben, weil der Nutzer es bewusst dort einsortiert hat.
- **Ausnahme Gruppen:** Erkennt die Verarbeitung weitere Personen im Bild, werden für diese **Kopien** in deren Ordnern erstellt. Die ursprüngliche, fixe Zuordnung bleibt unangetastet.

### 6.1b Eigenständige Faces (Face-Original)

Wird ein Gesichtsbild direkt als Face-Original einsortiert, ist es bereits der Crop — daher entfällt die Schwerarbeit teilweise:

- **Keine Face-Detection, keine Extraction/Crop** — das Bild ist selbst das Face.
- **Embedding wird trotzdem berechnet** (direkt auf dem Bild), denn ohne Embedding ist das Face nicht matchbar (Personen-Zuordnung, Top-Matches, Dedupe). Optional vorab eine reine Landmark-Detection zur Ausrichtung, falls die Embedding-Qualität es erfordert.
- **Restliche Verarbeitung nach Bedarf:** Embedding/Alter (`buffalo_l`), Tags, Caption, CLIP-Embedding und Qualität laufen wie gehabt (Framing ist trivial „close_up"). Thumbnail wird erzeugt.

### 6.2 Klassifizierungs-Matrix

| Dimension | Methode | Modell |
|---|---|---|
| Metadaten | Datei-Auslesen (EXIF) | — |
| Quelle (Original/SDXL/Flux) | PNG-Chunks / EXIF-Workflow | — |
| Framing (Close-Up/Medium/Full Body) | Heuristik (BBox/Bild) | — |
| Qualität (Auflösung, Face-Größe, Artefakte) | Messung + Blur-Heuristik | — |
| Alter | Attribut aus Face-Pack | `buffalo_l` |
| Face Detection / Recognition | Detection + ArcFace-Embedding | `buffalo_l` |
| Tags (inkl. Brille, Frisur, Haarfarbe, Outfit-Typ) | automatisch + manuell | WD14 |
| Caption (natürliche Sprache / Tags) | Vision-Language, konfigurierbar | Florence-2 (Default) · optional Qwen-VL / JoyCaption |
| Semantische Suche (Bild-Embedding) | CLIP/SigLIP-Embedding | CLIP / SigLIP (ONNX) |
| Zugehörigkeit (Film/Serie/Producer) | **nur manuelles Tagging** | — |

Bewusst **nicht** im Konzept: NSFW-Klassifizierung, Stil-Klassifizierung, automatische Outfit-/Kostüm-Erkennung (Outfit ggf. über Auto-/Manual-Tags).

---

## 7. Face Detection, Recognition & Zuordnung

- **Modell:** InsightFace `buffalo_l` (Detection + ArcFace-Recognition + Landmarks + Age/Gender), als ONNX über ONNX Runtime betrieben.
- **Extraktion:** Gesichter werden mit Padding zugeschnitten und in `personX/faces/` abgelegt — pro Person nur deren Gesichter.
- **Automatische Zuordnung:** Embeddings werden geclustert (HDBSCAN). Neue Faces werden per Cosine-Ähnlichkeit gegen bestehende Personen gematcht. Bilder mit `fixed_person = true` (manuell einsortiert) werden nicht automatisch umverteilt.
- **Manuelle Korrektur (überschreibt falsches Face-Match):** Eine falsche automatische Zuordnung wird korrigiert, indem dem Bild manuell die richtige Person zugewiesen wird; die Bilddatei wandert **physisch** in den richtigen Person-Ordner, Embeddings/DB werden umgehängt. Damit fällt das Bild auch aus dem Smart-Album der falschen Person heraus (siehe 10.1). So enthält jeder Person-Ordner tatsächlich rein nur Bilder dieser Person.
- **Top-Matches:** Für ein gegebenes Face liefert die Vektorsuche (`sqlite-vec`/FAISS) die **Top 10 disjunkten Personen** — also den jeweils besten Treffer **pro Person**, nicht zehn Bilder derselben Person. Der **Ähnlichkeits-Score (Threshold) wird in der Oberfläche angezeigt** (z.B. „92%"), damit die Treffer besser eingeordnet werden können.
- **Personen mergen / splitten:** Zwei Cluster, die dieselbe Person sind, lassen sich zusammenführen (inkl. physischem Verschieben aller Bilder in den Ziel-Ordner); ein verunreinigter Cluster lässt sich aufteilen.
- **Review-Queue:** Vorgeschlagene, unsichere Zuordnungen landen in einer Bestätigen/Ablehnen-Queue (Google-Fotos-Stil). Bestätigte Zuordnungen verschieben das Bild, abgelehnte wandern zurück nach `_unknown` oder zur Korrektur.
- **Eigenständige Faces (ohne Original):** Ein Face-Bild kann direkt manuell einsortiert werden — dann ist dieses Bild selbst das Original (`face.asset_id = NULL`, `origin = manual_original`). Es hat kein zugrundeliegendes Foto, ist einer Person zugeordnet und voll editierbar. **Detection und Extraction entfallen** (das Bild ist bereits der Crop); nur das Embedding wird berechnet, damit das Face matchbar bleibt (siehe 6.1b).

---

## 8. Edits, Upscale & Versionierung

### 8.1 Edit-Operationen

| Operation | Single | Bulk | Modell | Hinweis |
|---|---|---|---|---|
| Zuschneiden (frei + fixe Ratios) | ✓ | ✓ | — | kann Framing/Personen ändern |
| Smart-Crop auf Gesicht | ✓ | ✓ | `buffalo_l` | automatisch auf erkanntes Gesicht zentriert |
| Pad-to-Square / Aspect-Ratio | ✓ | ✓ | — | für Trainingsset-Buckets, ohne Beschnitt |
| Drehen | ✓ | ✓ | — | |
| Spiegeln | ✓ | ✓ | — | |
| PNG/JPEG-Konvertierung | ✓ | ✓ | — | JPEG verlustbehaftet, Alpha geht verloren; Quality-Option |
| Hintergrund entfernen | ✓ | ✓ | rembg (ONNX) | sauberer Subjekt-Crop |
| Upscale | ✓ | ✓ | SeedVR2 / Flux2 | tauscht Foto gegen Upscale |
| Flux2-Edit (img2img) | ✓ | ✓ | Flux2 | Prompt + Templates |
| Inpainting (Objekt-/Artefakt-Entfernung) | ✓ | — | Flux2 | Maske + Cleanup |
| Re-Import editierter Bilder | ✓ | ✓ | — | als neue Version ergänzen |

> **Edit-Ziele:** Alle Operationen lassen sich nicht nur auf Original-Fotos anwenden, sondern auch auf **Face-Crops** (inkl. eigenständiger Faces) und auf **bestehende Edits**. Ein Edit eines Edits oder ein Upscale eines Face hängt sich als weitere Version per `parent_id` an die Kette (bei Faces über `version.face_id`).

### 8.2 Versionierung & History

Zwei klar getrennte Schichten:

**a) Flüchtige Bearbeitungs-History (in der Cache-DB)**
- **Jeder Step und jeder Edit wird in der Thumbnail-/Cache-DB (`thumbnails.sqlite`) versioniert gespeichert** — als Operation + Parameter plus Vorschau-BLOB. Das erlaubt jederzeit **Rollback** auf einen beliebigen früheren Schritt, auch über die Session hinaus.
- Diese History ist **flüchtige Daten** — genau wie die Thumbnails. Sie lebt in der Cache-DB und hat **im Dateisystem nichts verloren**. Geht der Cache verloren, ist die Schritt-History weg, die gespeicherten Edits im Dateisystem bleiben.
- Das **Original ist unveränderlich** und bleibt Ausgangspunkt jeder History.

**b) Persistente, gespeicherte Edits (im Dateisystem)**
- **Ins Dateisystem (`personX/edits/`) wird erst durch aktives Speichern geschrieben.** Solange der Nutzer nicht speichert, existiert ein Edit nur als flüchtige History in der Cache-DB.
- **Weiteres Editieren & Speichern** bietet zwei Wege, die der Nutzer aktiv wählt:
  - **Überschreiben** des bestehenden Edits, oder
  - **Als neue Kopie** (zusätzlicher Edit) ablegen.
- Der Nutzer hat damit **jederzeit volle Kontrolle**, welche Edits er wie speichert. In der DB (`db.sqlite`) werden gespeicherte Edits über `version` mit `parent_id` und `is_current` geführt; „Foto gegen Edit/Upscale austauschen" wechselt nur den aktiven Zeiger, ältere gespeicherte Edits bleiben erhalten.

### 8.2a Sonderfall Crop (Personen fallen heraus)

Schneidet ein Crop eine Person aus dem Bild heraus, wird der bearbeitete Edit **nicht** als Kopie zu dieser Person gespeichert. Das **Original mit dieser Person bleibt** jedoch als Kopie in deren Ordner erhalten. Der Edit wird nur den Personen zugeordnet, die nach dem Crop noch im Bild sind.

### 8.3 Effiziente Neuverarbeitung (Edits/Upscales)

Edits und Upscales werden **nicht** erneut getaggt, captioned oder klassifiziert — sie erben die semantischen Daten vom Eltern-Asset. Erneut berechnet werden nur **gemessene** Attribute (Auflösung, Face-Größe, Qualität).

Das Einzige, was inhaltlich neu hinzukommt: höher aufgelöste Faces (Upscale) bzw. leicht andere Posen (Flux-Edit). Logik pro neuer Version:

1. Face Detection auf der neuen Version ausführen, Crops ziehen.
2. Pro Crop einen **perceptual Hash (pHash)** berechnen und gegen die vorhandenen Crops derselben Lineage (gleicher Hash + Person) vergleichen.
3. **pHash quasi identisch →** kein neues Face (z.B. Spiegeln, Drehen, Konvertierung, marginale Edits).
4. **pHash deutlich abweichend →** neues Face ablegen, mit Provenienz markieren (`origin_type`, `source_version_id`).
5. **Sonderfall Upscale:** auch bei visuell gleichem Crop behalten, wenn die Auflösung klar höher ist (`is_upscaled = true`); der alte, kleinere Crop kann als überholt markiert werden.

> **pHash ≠ Embedding:** Der pHash beantwortet „ist dieser Crop *visuell* ein Duplikat?" (→ keep/skip). Das Embedding beantwortet „*wer* ist das?" (→ Personen-Zuordnung). Das Embedding läuft nur auf behaltenen Crops zur Bestätigung der Person.

### 8.4 Flux2-Prompt-Templates

Wiederverwendbare Prompt-Bausteine für gute Edits: gespeichert in `prompt_template` (Name, Prompt-Text, Parameter wie Strength/Steps/Guidance/Seed). Platzhalter wie `{person}` werden beim Einsetzen ersetzt. In der Edit-UI per Klick anwendbar, single und bulk.

---

## 9. Trainingssets

Trainingssets sind speziell ausgestattete Collections (`collection.kind = 'training_set'`):

- **Statistiken & Verteilung:** Übersicht über Framing-Verteilung (Close-Up / Medium / Full Body), Tag-Häufigkeiten, Qualität, **Aspect-Ratio-Bucket-Verteilung** (Kohya-Style) und **Near-Duplicate-Quote**.
- **Auto-Tagging / Caption-Erstellung** direkt im Set.
- **Bearbeiten von Tags und Captions** (Override pro Bild via `caption_override`).
- **Caption-Tools über das ganze Set:** Trigger-Word voranstellen, Prefix/Suffix anhängen, Find-Replace über alle Captions.
- **Near-Duplicate-Warnung & Vergleich:** Das Set wird per pHash auf zu ähnliche Bilder geprüft (verzerren das Training). Ähnliche Paare können im **Links-Rechts-Vergleich** geprüft werden — pro Paar lässt sich aktiv entscheiden: eines behalten, das andere behalten oder beide behalten. Verworfene wandern in den Papierkorb.
- **Train/Val-Split** beim Export einstellbar.
- **Upscale** und **Edit-Features** im Set nutzbar (tauschen das Foto gegen Upscale/Edit aus, rückgängig machbar).
- **Export mit Captions:** Sidecar-`.txt` pro Bild, **wahlweise Tags, Caption oder beides** (in der Export-Option wählbar). Diese Sidecars sind reine Export-Artefakte für das Training und betreffen nicht die Galerie-Ablage.

---

## 10. Suche, Filter, Gruppierung, Sortierung

**Suche & Filter:**
- nach Person, Face, Klassifizierung, Tags
- **Semantische Suche** per CLIP/SigLIP-Embedding: Freitext → Bild („Frau im roten Kleid am Strand") sowie „mehr wie dieses" über Bild-Ähnlichkeit. Ergänzt Tag-Facetten und Caption-Volltext zu drei Such-Ebenen.
- **Top 10 disjunkte Personen** für ein gegebenes Face (bester Treffer je Person), mit angezeigtem Ähnlichkeits-Score
- **Duplikate mit prozentualer Ähnlichkeit:** perceptual Hash → Hamming-Distanz wird in einen Prozentwert umgerechnet und angezeigt; einstellbarer Schwellwert. Optional zusätzlich Embedding-Cosine-Similarity für semantische Duplikate (gleiche Szene, andere Pose). Bewusst beschränkt auf die Suche innerhalb eines Person-Ordners.

**Tags & Captions — manuell korrigierbar:**
- WD14-Tags und Captions sind **pro Bild manuell editierbar** (hinzufügen, entfernen, ändern) — nötig, um Modellfehler zu kompensieren. Manuelle Korrekturen werden gegenüber Re-Klassifizierungen als bevorzugt markiert.
- **Tag-Verwaltung:** Umbenennen, Mergen, Aliase (über `tag.alias_of`), Bulk-Editing; optional Tag-Hierarchie. Hält den bei zigtausend Auto-Tags entstehenden Wildwuchs beherrschbar.
- Jede Änderung an Tags, Caption oder Personen-Zuordnung stößt die Neubewertung der Smart-Album-Mitgliedschaft an (siehe unten).

**Gruppierung:**
- nach Person
- eigene Collections / Alben (manuell befüllt)
- **Smart-Alben** (Trigger-basiert, automatisch befüllt — siehe 10.1)
- nach Original / Face / Edit (das Originalbild und alle abgeleiteten Versionen als Einheit)

**Sortierung:**
- nach Datum
- nach Größe

**Detailansicht:**
- **Generierungs-Metadaten-Viewer:** zeigt bei AI-Bildern den eingebetteten Prompt/Workflow (aus `generation_meta`).
- **Side-by-side-Vergleich:** Original vs. Upscale vs. Edit nebeneinander.

### 10.1 Smart-Alben (Trigger-basiert)

Wie bei Google Fotos kann der Nutzer einem Album **Trigger** hinzufügen, die das Album automatisch befüllen. Die Trigger werden am Album selbst konfiguriert.

**Trigger-Typen:**
- **Person:** Wird eine bestimmte Person im Bild erkannt, landet das Bild automatisch im Album.
- **Tag:** Enthält ein Bild einen bestimmten WD14-Tag, landet es automatisch im Album.
- **Caption:** Enthält die Caption ein bestimmtes Wort oder eine Phrase, landet das Bild automatisch im Album.

**Verhalten:**
- Mehrere Trigger lassen sich über `match_mode` verknüpfen: **any** (ein Treffer genügt) oder **all** (alle müssen zutreffen). Optional negierbare Trigger (Ausschluss).
- **Automatisches Hinzufügen *und* Entfernen:** Ändern sich die zugrundeliegenden Daten (Tag entfernt/ergänzt, Caption bearbeitet, Person neu zugeordnet), wird die Mitgliedschaft neu bewertet — passende Bilder kommen hinzu, nicht mehr passende fallen wieder heraus.
- Smart-Mitgliedschaften werden in `collection_item` mit `source = 'smart'` materialisiert (schnelle Anzeige), getrennt von manuell hinzugefügten Einträgen.
- **Auslöser der Neubewertung:** jede Änderung an Tags, Caption oder Personen-Zuordnung eines Bildes (auch manuelle Korrekturen) sowie das Hinzufügen/Ändern eines Triggers. Die Neubewertung läuft über die Queue, damit die UI nicht blockiert.

**Voraussetzung — Korrektur an der Wurzel (kein manueller Exclude):** Ein Bild wird nicht direkt aus einem Smart-Album geworfen, sondern über die Korrektur der zugrundeliegenden Daten:
- **Tag-/Caption-Trigger:** den unpassenden Tag entfernen bzw. die Caption anpassen — das Bild fällt bei der Neubewertung aus dem Album. Tags und Captions sind dafür pro Bild manuell editierbar (kompensiert Modellfehler).
- **Personen-Trigger:** ein falsches Face-Match überschreiben und manuell die richtige Person zuweisen — dadurch fällt das Bild aus dem Album der falschen Person.

In beiden Fällen erfolgt die Aktualisierung automatisch über die Trigger-Neubewertung; einen separaten „aus Album entfernen"-Override gibt es bewusst nicht.

---

## 11. Import & Export

**Import:**
- Single
- Bulk
- Dateisystem-Scan nach neuen Bildern → automatische Klassifizierung und Queue
- manuell in Person-Ordner eingeschobene Bilder werden erkannt und verarbeitet (Person fix, Gruppen-Kopien als Ausnahme — siehe 6.1a)
- bei neuem Bild: Face automatisch mit Padding extrahieren (in `personX/faces/`), Kopien für weitere erkannte Personen anlegen
- **direkter Face-Import:** ein Gesichtsbild kann direkt zu einer Person einsortiert werden — es wird dann als eigenständiges Original behandelt (kein zugrundeliegendes Foto) und ist voll editierbar

**Export:**
- Im Dateisystem anzeigen
- alle Bilder des aktuellen Filters exportieren
- alle Bilder der aktuellen Gruppierung exportieren (z.B. Original + alle Ableitungen)
- alle Favoriten exportieren (in Ordner sortiert nach Person)
- zufällige Favoriten exportieren (Anzahl Exporte × Bilder einstellbar, z.B. 5×100, distinct ohne Duplikate; Dateinamen mit Person ergänzt)
- eigene Collections / Alben exportieren
- Trainingssets mit Sidecar-`.txt` (wahlweise Tags, Caption oder beides)

---

## 12. Modell-Management & Varianten

### 12.1 Konfigurationsseite

- **Keine Modelle im Repository.** Die README dokumentiert ausführlich, wo welches Modell zu beziehen ist (Quelle, gepinnte Version, Lizenz).
- **Frei wählbarer Default-Download-Ordner:** Das Download-Ziel wird **über die UI festgelegt** (Verzeichnis-Picker) und in `app_config` (`models_dir`) gespeichert. Default ist ein Pfad im App-Verzeichnis; der Nutzer kann ihn aber auf ein beliebiges Verzeichnis legen (z.B. eine separate Modell-Platte). **Alle per Settings heruntergeladenen Modelle landen genau dort.** Eine Pfadänderung gilt für **neue** Downloads; vorhandene Einträge behalten ihren absoluten Pfad bzw. werden auf Wunsch migriert.
- **Drei Wege, ein Modell bereitzustellen (pro Modell wählbar):**
  1. **In-App-Download** per Button (läuft über die Queue, landet im Default-Download-Ordner) → `managed = 1`.
  2. **Manueller Drop** in den Download-Ordner, anschließend „Erkennen/Scannen" → `managed = 1`.
  3. **Vorhandene Datei(en) in-place einbinden** → `managed = 0`: bereits auf dem System liegende Modelle werden direkt referenziert, **statt sie doppelt herunterzuladen** (z.B. ein ComfyUI-/A1111-Bestand). Es wird **weder kopiert noch verschoben noch verändert**; beim Entfernen aus der Registry verschwindet nur der DB-Eintrag, die Datei bleibt liegen.
- **In-Place-Einbinden — drei Formen je nach Modell-Layout:**
  - **Einzeldatei:** ein Picker für eine einzelne Datei (z.B. ein GGUF-Captioner, ein einzelnes safetensors).
  - **Ordner-Modell:** ein **Ordner-Picker** für Modelle, die als Verzeichnis vorliegen (diffusers-Layout, `buffalo_l`-Bundle, WD14 mit CSV) — hier stimme ich zu: der ganze Ordner wird gewählt.
  - **Komponenten-Modell (z.B. Flux):** **jede Komponente einzeln auswählbar** über separate Picker — Diffusion-/Transformer-Modell, Text-Encoder, VAE. Diese liegen in der ComfyUI-Welt in **getrennten** Ordnern (`models/unet`, `models/clip` bzw. `text_encoders`, `models/vae`) und dürfen daher an **verschiedenen Orten** liegen. Die Pfade landen als benannte Map in `components`, z.B. `{"diffusion": …, "text_encoder": …, "vae": …}`.
- **Varianten je GPU:** Große Modelle werden in mehreren Varianten angeboten (fp16 / fp8 / GGUF-Q4). Die Seite empfiehlt anhand der erkannten VRAM eine Variante; manuelle Auswahl jederzeit möglich.
- **Integritätsprüfung:** Bei **managed** Modellen wird die SHA-256 nach dem Download gegen das Manifest geprüft. Bei **in-place** Modellen ist die Hash-Prüfung nur **informativ** (kann eine eigene Quantisierung sein, die nicht im Manifest steht) — stattdessen ein **Lade-/Validierungs-Check** je Komponente (Datei öffnet sich, Format passt zur erwarteten Rolle).
- **Gating:** Ein Feature bleibt deaktiviert mit Hinweis „Modell X fehlt", bis **alle** nötigen Teile vorhanden (egal ob managed oder in-place) und aktiviert sind — bei Komponenten-Modellen also erst, wenn Diffusion, Text-Encoder **und** VAE gesetzt sind.

### 12.2 Beschaffungs-Flow (in der UI)

**A) In-App-Download** — wird in der Konfigurationsseite ausgelöst, läuft über die Queue (mit Fortschritt und Feedback) und bezieht die gewählte Variante samt aller Begleitdateien (z.B. Text-Encoder, VAE). Ablauf pro Modell:

1. Nutzer wählt Modell + Variante (fp16/fp8/GGUF), bestätigt ggf. Lizenzhinweis.
2. Queue-Job lädt Haupt- + Begleitdateien in den konfigurierten **Modell-Ordner** (`app_config.models_dir`) herunter (Fortschrittsbalken im UI).
3. SHA-256-Prüfung gegen das Manifest.
4. Registrierung in `model_registry` (`managed = 1`), Feature wird aktiviert.

**B) Vorhandene Datei(en) in-place einbinden** — ohne erneuten Download:

1. Nutzer wählt „Vorhandene Datei verwenden". Je nach Modell-Layout erscheint:
   - **Einzeldatei** → ein Datei-Picker.
   - **Ordner-Modell** (diffusers, `buffalo_l`, WD14+CSV) → ein Ordner-Picker.
   - **Komponenten-Modell** (z.B. Flux) → **separate Picker je Komponente** (Diffusion, Text-Encoder, VAE) — Pfade können in verschiedenen Verzeichnissen liegen.
2. **Lade-/Validierungs-Check je Teil** (öffnet sich, Format passt zur Rolle); SHA-256 wird berechnet und **informativ** angezeigt.
3. Registrierung in `model_registry` mit **absoluten Originalpfaden** (`path` bzw. `components`) und `managed = 0` — kein Kopieren, kein Verschieben.

Das generative Backend (diffusers bzw. ComfyUI-Backend) muss das Laden von **fp8-safetensors** und **GGUF** unterstützen, damit die quantisierten Varianten tatsächlich nutzbar sind.

### 12.2a Validierung & Fehlermeldungen bei der Modellwahl

Die Modellwahl ist die fehleranfälligste Stelle (falsche Datei, falsche Rolle, inkompatible Komponente). Jeder Fehler wird **abgefangen, nicht verschluckt**, und jede Meldung nennt drei Dinge: **was erwartet wurde · was gefunden wurde · was zu tun ist**. Validiert wird **vor** der Aktivierung — kein halb-registriertes, nicht ladbares Modell darf ein Feature freischalten.

**Validierungsstufen (in dieser Reihenfolge):**

1. **Existenz/Zugriff** — Pfad existiert und ist lesbar.
2. **Format** — Dateiendung/Magic-Bytes passen zum erwarteten Format (`onnx` / `safetensors` / `gguf`).
3. **Rolle** — die Datei passt zur Rolle des Slots (ein Tagger-ONNX gehört nicht in einen Captioner-Slot; ein VAE nicht in den Diffusion-Slot).
4. **Vollständigkeit** — bei Komponenten-Modellen sind alle Pflichtteile gesetzt (Diffusion + Text-Encoder + VAE).
5. **Ladbarkeit** — Probe-Load in der Zielengine (ONNX-Session öffnen bzw. State-Dict-Header lesen), ohne vollständige Inferenz.
6. **Kompatibilität** (nur Warnung, s. 19.7) — Encoder-/VAE-Familie passt laut Manifest zum Diffusion-Modell.

**Fehlerklassen → Meldung (Beispiele):**

| Fehlerklasse | UI-Meldung (Muster) |
|---|---|
| Datei fehlt / kein Zugriff | „Datei nicht gefunden: `…/vae.safetensors`. Pfad prüfen oder neu auswählen." |
| Falsches Format | „Erwartet: `.safetensors` (VAE). Gefunden: `.ckpt`. Bitte eine safetensors-VAE wählen." |
| Falsche Rolle | „Diese Datei sieht aus wie ein **Text-Encoder**, gewählt wurde aber der **VAE**-Slot. Slot oder Datei korrigieren." |
| Komponente fehlt | „Flux unvollständig: **VAE fehlt**. Feature bleibt deaktiviert, bis Diffusion, Text-Encoder und VAE gesetzt sind." |
| Lade-/Validierungsfehler | „Datei ließ sich nicht laden (beschädigt oder inkompatibles Format). Originalmeldung der Engine: `…`." |
| VRAM zu klein | „Variante fp16 (~29 GB VRAM) übersteigt die erkannten 16 GB. Empfehlung: fp8- oder GGUF-Variante." |
| Hash-Abweichung (managed) | „Prüfsumme weicht vom Manifest ab — Download evtl. unvollständig. Erneut laden?" (in-place: nur informativer Hinweis, kein Abbruch) |
| Kompatibilitäts-Warnung | „Hinweis: Dieser Text-Encoder ist nicht die für dieses Diffusion-Modell erwartete Familie. Output kann fehlerhaft sein — trotzdem verwenden?" |

**Grundsätze:** Technische Roh-Exceptions werden **geloggt**, dem Nutzer aber in **verständliche Sprache** übersetzt (mit ausklappbarem Detail für Power-User). Ein gescheiterter Einbinde-Versuch lässt den vorherigen Zustand **unangetastet** (kein kaputter Teil-Eintrag in `model_registry`). Über die API werden Fehler als strukturierte Codes zurückgegeben (z.B. `MODEL_WRONG_ROLE`, `MODEL_INCOMPLETE`, `MODEL_LOAD_FAILED`), die das Frontend auf die obigen Meldungen mappt.

| Modell | Rolle | Format | Größe ≈ | Lizenz | Tier |
|---|---|---|---|---|---|
| InsightFace `buffalo_l` | Face | ONNX (Bundle) | ~280 MB | Code MIT, Weights gesondert | Core / onnxruntime |
| WD14 `swinv2-v3` (Default) | Tagger | ONNX + CSV | ~300–400 MB | permissiv | Core / onnxruntime |
| WD14 `vit-large` / `eva02-large-v3` | Tagger (hochgenau) | ONNX | ~1,2 GB | permissiv | optional |
| Florence-2-base (Default) | Captioner (`task_token`) | ONNX / safetensors | ~0,46 GB | MIT | Core / onnxruntime |
| CLIP / SigLIP | Semantische Suche | ONNX | ~0,3–0,9 GB | permissiv | Core / onnxruntime |
| rembg (u2net/isnet) | Hintergrund entfernen | ONNX | ~40–180 MB | permissiv | Core / onnxruntime |
| Florence-2-large | Captioner (`task_token`) | ONNX / safetensors | ~1,5 GB | MIT | optional |
| JoyCaption | Captioner (`instruct_guided`) | safetensors | ~16–17 GB | prüfen | heavy / torch |
| Qwen2.5-VL 7B | Captioner (`instruct`) | safetensors | mehrere GB | meist Apache | heavy / torch |
| FLUX.2 [klein] 9B | Edit + Upscale | safetensors (+GGUF) | 18,2 GB (bf16) / ~9 GB (fp8) | **non-commercial** | generativ |
| SeedVR2 3B | Upscale | safetensors (+GGUF) | 6,2 / 3,4 / 1,9 GB | apache-2.0 | generativ |
| SeedVR2 7B | Upscale | safetensors (+GGUF) | 14,5 / 8,2 / 4,6 GB | apache-2.0 | generativ |

### 12.4 Varianten- & VRAM-Matrix (generativ)

| Modell | Variante | Größe ≈ | VRAM ≈ |
|---|---|---|---|
| FLUX.2 klein 9B | bf16 | 18,2 GB | ~29 GB |
| | fp8 | ~9 GB | ~24 GB |
| | GGUF-Q4 (Community) | kleiner | niedriger |
| SeedVR2 3B | fp16 | 6,2 GB | 16 GB+ |
| | fp8 | 3,4 GB | ~12 GB |
| | GGUF-Q4 | 1,9 GB | 8 GB (BlockSwap) |
| SeedVR2 7B | fp16 | 14,5 GB | 20 GB+ |
| | fp8 | 8,2 GB | ~16 GB |
| | GGUF-Q4 | 4,6 GB | ~12 GB |

> FLUX.2 klein 9B benötigt zusätzlich einen separaten Text-Encoder (Qwen3) und eine VAE (~168 MB); SeedVR2 eine eigene VAE (~500 MB). Der In-App-Download holt diese Begleitdateien mit; beim **In-Place-Einbinden** werden Diffusion-Modell, Text-Encoder und VAE **einzeln** ausgewählt (`components`, s. 12.1).

### 12.5 Inferenz-Tiers

- **Core (immer, ONNX Runtime, läuft notfalls auf CPU):** `buffalo_l` + WD14 + Florence-2-base + CLIP/SigLIP + rembg ≈ **~1,5–2 GB** gesamt. Privacy-sauberer Pflicht-Stack ohne torch.
- **Optional heavy (torch):** große Captioner — nur bei Aktivierung installiert/geladen.
- **Generativ (torch/diffusers o. ComfyUI, GPU):** Flux2 + SeedVR2 — zweistellige GB Disk und VRAM, vollständig gated.

### 12.6 Captioner-Settings pro Modell (UI)

Jeder Captioner hat eine **andere Bedien-Schnittstelle**. Die Settings-UI darf deshalb nicht für alle Modelle dasselbe Panel zeigen — sie rendert die Steuerelemente **deklarativ aus dem `capabilities`-Descriptor** des jeweiligen Modells (`model_registry.capabilities`), gesteuert über `caption_mode`. So erscheint nur, was das Modell auch versteht: kein erfundenes System-Prompt-Feld bei Florence-2, keine Task-Token-Auswahl bei Qwen.

**Drei Captioner-Modi:**

| `caption_mode` | Bedeutung | Beispiel |
|---|---|---|
| `task_token` | feste Task-Tokens, **kein** freier Prompt | Florence-2 |
| `instruct` | freier System-/User-Prompt + Sampling | Qwen2.5-VL |
| `instruct_guided` | geführter Prompt-Builder aus Bausteinen | JoyCaption |

**Presets:** `caption_preset` speichert pro Modell eine **benannte, wiederverwendbare** Konfiguration (`config` JSON, modus-spezifisch). So stehen z.B. „Natürliche Sprache" und „Danbooru-Tags" nebeneinander; beim Caption-Lauf wählt der Nutzer **Modell + Preset**. Jede Caption merkt sich via `asset.caption_preset_id`, womit sie erzeugt wurde (Provenienz, wichtig für konsistente Trainingssets).

#### Florence-2 — `task_token`

| Steuerelement | Typ | Default | Erklärung in der UI |
|---|---|---|---|
| Task-Token | Dropdown | `<DETAILED_CAPTION>` | Steuert die Ausführlichkeit: `<CAPTION>` = ein Satz, `<DETAILED_CAPTION>` = mehrere Sätze, `<MORE_DETAILED_CAPTION>` = ausführlich. |
| `max_new_tokens` | Zahl | 1024 | Obergrenze der Ausgabelänge. |
| `num_beams` | Zahl | 3 | Beam-Search-Breite. Höher = tendenziell bessere, aber langsamere Ergebnisse. |

> **UI-Hinweis (Info-Box):** Florence-2 folgt **keinen** freien Anweisungen und kennt kein Temperatur-Sampling (deterministische Beam-Search). Stil und Länge steuerst du ausschließlich über das **Task-Token** — es gibt hier bewusst **kein System-Prompt-Feld**.

#### Qwen2.5-VL — `instruct`

| Steuerelement | Typ | Default | Erklärung in der UI |
|---|---|---|---|
| System-Prompt | Textarea | aus Preset | **Wichtigster Hebel.** Bestimmt den Ausgabestil — natürliche Prosa **oder** komma-getrennte Tags. |
| User-Prompt | Textfeld | „Describe this image." | Konkrete Aufgabe pro Bild. |
| `temperature` | Slider 0–1.5 | 0.7 | Niedrig = nüchtern/deterministisch, hoch = kreativer/variabler. |
| `top_p` | Slider 0–1 | 0.9 | Nucleus-Sampling. |
| `max_new_tokens` | Zahl | 512 | Obergrenze der Ausgabelänge. |
| `repetition_penalty` | Zahl | 1.05 | Dämpft Wortwiederholungen. |
| `min_pixels` / `max_pixels` | Zahl | 256·28² / 1280·28² | Bild-Token-Budget: mehr = feinere Details, aber mehr VRAM und langsamer. |

> **UI-Hinweis (Info-Box):** Qwen2.5-VL folgt Instruktionen — der Ausgabestil ergibt sich aus dem **System-Prompt**. Für Booru-Stil entsprechend instruieren; das Ergebnis ist jedoch **tag-geflavorte Prosa**, keine echte Danbooru-Taxonomie. Für vokabular-treue Booru-Tags ist **WD14** das Werkzeug.

#### JoyCaption — `instruct_guided`

| Steuerelement | Typ | Default | Erklärung in der UI |
|---|---|---|---|
| Caption-Typ | Dropdown | Descriptive | Descriptive · Straightforward · Stable-Diffusion-Prompt · Booru-Tag-Liste · Art-Critic · Product-Listing · Social-Media-Post … |
| Länge | Dropdown | medium | any · very short · short · medium · long · very long (oder feste Wortzahl). |
| Extra-Optionen | Checkboxen | — | z.B. Beleuchtung nennen, Kamerawinkel angeben, Wasserzeichen erwähnen/ignorieren. |
| Person-Name | Textfeld | optional | Wird, falls gesetzt, in die Caption eingebaut. |
| Raw-Prompt-Override | Textarea (Advanced) | leer | Überschreibt den generierten Prompt für Power-User. |

> **UI-Hinweis (Info-Box):** JoyCaption baut den Prompt **aus Bausteinen** (Typ + Länge + Optionen) — ein roher System-Prompt ist nur im **Advanced-Override** nötig.

---

## 13. Wartung, Datensicherheit & Bedienung

Alles in dieser Sektion ist **über die UI** bedienbar — keine Skripte.

### 13.1 DB-Backup
- DB-Snapshots können **aktiv exportiert** werden (Button), Ablage in `.photofant/backups/` oder an einen wählbaren Ort.
- Da Metadaten ausschließlich in der DB liegen, ist das regelmäßige Backup die empfohlene Absicherung gegen den bewusst akzeptierten Datenverlust.

### 13.2 FS↔DB-Reconciliation (Verify & Repair)
- **Manuell anstoßbarer Scan**, der Dateisystem und DB abgleicht: verwaiste Dateien (im FS, nicht in DB), fehlende Dateien (in DB, nicht im FS) und Pfad-Drift nach manuellen Moves.
- Ergebnis als Report mit Reparatur-Optionen (neu indizieren, als fehlend markieren, in Papierkorb).

### 13.3 Thumbnail-/Face-Rebuild
- **Thumbnail-Rebuild:** generiert `thumbnails.sqlite` komplett aus den vorhandenen Bildern neu (jederzeit gefahrlos, da reiner Cache).
- **Face-Rebuild (optional):** re-extrahiert die **abgeleiteten** Face-Crops aus den Fotos in `personX/faces/`. **Manuelle Face-Originale (`origin = manual_original`) werden dabei nie überschrieben.**

### 13.4 Papierkorb (Soft-Delete)
- Löschen setzt `deleted_at` und verschiebt die Datei nach `.photofant/trash/`. Wiederherstellung und endgültiges Löschen über die UI; optionale Aufbewahrungsfrist. Schützt vor Fehlklicks bei Bulk-Operationen.

### 13.5 Bedienung & Shortcuts
- **Tastatur-Shortcuts** für häufige Aktionen (Favorit, nächstes/vorheriges Bild, Tag-Quick-Add, Löschen, Navigation).
- **Shortcut-Legende** (Overlay) und **Anpassung der Belegung in den Settings**.
- Rubber-Band-Mehrfachauswahl im Grid für Bulk-Operationen.

---

## 14. API-Design (FastAPI, Auszug)

```
GET    /assets                      # Liste mit Filter/Sortierung/Pagination
GET    /assets/{id}                 # Detail inkl. Versionen, Faces, Tags, Generierungs-Meta
GET    /assets/{id}/thumbnail       # Thumbnail (aus thumbnails.sqlite, Cache-Header)
PATCH  /assets/{id}/tags            # manuelle Tag-Korrektur (add/remove) → triggert Smart-Album-Neubewertung
PATCH  /assets/{id}/caption         # manuelle Caption-Korrektur → triggert Smart-Album-Neubewertung
POST   /assets/import               # Single/Bulk-Import
POST   /assets/scan                 # Dateisystem-Scan (neue Bilder)
POST   /search/semantic             # CLIP/SigLIP: Freitext oder "mehr wie dieses"

GET    /persons                     # Personen + Stats
PATCH  /faces/{id}/assign           # manuelle Korrektur (verschiebt Bilddatei)
GET    /faces/{id}/matches          # Top 10 disjunkte Personen + Score
POST   /persons/merge               # zwei Personen zusammenführen
POST   /persons/{id}/split          # Cluster aufteilen
GET    /review-queue                # unsichere Zuordnungen bestätigen/ablehnen

POST   /assets/{id}/edit            # crop/smart-crop/pad/rotate/mirror/convert/rembg (Bulk via Body)
POST   /assets/{id}/upscale         # SeedVR2/Flux2
POST   /assets/{id}/flux-edit       # img2img + Template
POST   /assets/{id}/inpaint         # Flux2 Inpainting (Maske)
POST   /assets/{id}/save-version    # bewusstes Speichern → neue Version
POST   /assets/{id}/undo            # auf frühere gespeicherte Version zurück

GET    /tags                        # Liste
POST   /tags/merge                  # Mergen/Alias
PATCH  /tags/{id}                   # Umbenennen
POST   /tags/bulk                   # Bulk-Tagging

GET    /collections                 # Alben + Trainingssets + Smart-Alben
GET    /collections/{id}/triggers    # Smart-Album-Trigger lesen
POST   /collections/{id}/triggers    # Trigger hinzufügen (person/tag/caption) → Re-Scan
DELETE /collections/{id}/triggers/{tid} # Trigger entfernen → Re-Scan
POST   /collections/{id}/reevaluate  # Smart-Album-Mitgliedschaft neu berechnen
POST   /collections/{id}/export     # Export mit Optionen (inkl. Train/Val-Split)
POST   /collections/{id}/captions   # Trigger-Word / Prefix / Suffix / Find-Replace
GET    /collections/{id}/duplicates # Near-Dupe-Paare für Links-Rechts-Vergleich
POST   /export/favourites/random    # Zufalls-Favoriten-Export
POST   /duplicates/search           # Duplikate inkl. Ähnlichkeits-% (Threshold)

DELETE /assets/{id}                 # Soft-Delete → Papierkorb
GET    /trash                       # Papierkorb-Inhalt
POST   /trash/{id}/restore          # wiederherstellen
DELETE /trash/{id}                  # endgültig löschen

GET    /prompt-templates            # CRUD
GET    /models                      # Registry-Status
POST   /models/{id}/download        # In-App-Download (läuft über Queue)
POST   /models/register-local       # vorhandene Datei/Ordner in-place einbinden (managed=0)
GET    /config                      # App-Config lesen (u.a. models_dir)
PATCH  /config                      # App-Config setzen (z.B. Modell-Ordner wählen)
GET    /caption-presets             # CRUD (optional ?model_id=)
POST   /caption-presets             # Preset anlegen (modus-spezifischer config-JSON)
PATCH  /caption-presets/{id}        # Preset bearbeiten
DELETE /caption-presets/{id}
POST   /classify/rerun              # Captioner/Klassifizierer neu (Single/Bulk), optional caption_preset_id

POST   /maintenance/backup          # DB-Snapshot exportieren
POST   /maintenance/reconcile       # FS↔DB-Scan (Verify & Repair)
POST   /maintenance/rebuild         # Thumbnails/Faces neu generieren

WS/SSE /jobs/stream                 # Fortschritt aller Queue-Jobs (inkl. Downloads)
```

---

## 15. NgRx State-Design (Feature-Slices)

- **gallery** — Asset-Entities (Entity-Adapter), seitenweise Pagination (kein Virtual Scroll)
- **filters** — aktive Filter/Sortierung/Gruppierung
- **search** — semantische Suche (CLIP), Ergebnisse + Scores
- **selection** — Mehrfachauswahl für Bulk-Operationen
- **persons** — Personen, Faces, Top-10-Personen-Matches inkl. Score, Merge/Split, Review-Queue
- **editor** — aktive Edit-Session, **temporäre In-Memory-Step-Historie** (wird beim Speichern verworfen), gespeicherte Versionen
- **tags** — Tag-Verwaltung (Merge/Alias/Bulk)
- **collections** — Alben, Trainingssets (Caption-Tools, Near-Dupe-Vergleich), Smart-Alben, Stats
- **promptTemplates** — Templates für Flux2-Edits
- **trash** — Papierkorb-Inhalt
- **maintenance** — Backup, Reconciliation, Rebuild (Status/Reports)
- **jobs** — Queue-Status/Fortschritt aller Hintergrund-Tasks inkl. Downloads (über SSE-Effects)
- **settings** — Default-Tagger/Captioner, **Modell-Ordner-Pfad**, Modell-Registry (Beschaffung: Download / In-Place), Varianten, **modellspezifische Captioner-Settings + Caption-Presets** (s. 12.6), **Shortcut-Belegung**

Effects kapseln alle API-Aufrufe; der Job-Stream aktualisiert den `jobs`-Slice live.

---

## 16. Performance & Responsiveness

- **Pagination statt Virtual Scroll:** das Thumbnail-Grid wird seitenweise geladen (server-seitige Pagination), kein virtualisiertes Endlos-Scrolling.
- **Thumbnails** in mehreren Größen vorgeneriert, mit Cache-Headern ausgeliefert.
- **Alles potenziell Langsame läuft über die Queue:** Import, Klassifizierung, Face-Extraction, Edits, Upscales, Exporte und Modell-Downloads. Die App darf unter keinen Umständen ruckeln oder hängen — die UI blockiert nie auf einer langen Operation.
- **Durchgängiges Frontend-Feedback:** Ladeanimationen, Skeletons, Fortschrittsbalken (gespeist aus dem `jobs`-Stream), optimistische UI-Updates und Mikrointeraktionen sorgen dafür, dass sich die gesamte App jederzeit responsive anfühlt.
- **Indizierte DB-Abfragen** für Filter/Sortierung; Faceting über die `tag`/`asset_tag`-Struktur.
- **Vektorsuche** (`sqlite-vec`/FAISS) für Face-Top-Matches und Clustering.

---

## 17. Install & Start

- **`install`-Skripte:** virtuelle Umgebung, gepinnte Dependencies (Lockfile), `onnxruntime` als Pflicht; torch/diffusers nur bei aktivierten generativen Features. Bereitgestellt als `install.sh` (Linux/macOS) **und `install.cmd` (Windows)**.
- **`start`-Skripte:** Backend (Uvicorn) hochfahren, Frontend-Build statisch ausliefern (oder Dev-Server). Als `start.sh` **und `start.cmd` (Windows)**.
- **Modell-Downloads:** ausschließlich über die UI (Konfigurationsseite), nicht über Skripte.
- **Offline-Garantie:** `HF_HUB_OFFLINE=1` / `TRANSFORMERS_OFFLINE=1` setzen, sobald torch-basierte Modelle aktiv sind. ONNX Runtime ist von Haus aus offline.
- **Robustheit:** Modell-Binaries als externe Downloads, niemals als Plain-Git-Commit; Dependency-Versionen pinnen.

---

## 18. Feature-Roadmap (inkrementell)

Jede Stage ist für sich nutzbar und baut auf der vorherigen auf. Generative Features (Stage 5) sind optional und können bei Bedarf vorgezogen oder parallel entwickelt werden, ohne die Kern-Stages zu blockieren.

### Stage 0 — Fundament (Walking Skeleton)
- Repo-Struktur, `install`/`start`-Skripte (inkl. Windows `.cmd`), Lockfile.
- FastAPI-Skeleton, Angular + Tailwind + NgRx-Skeleton, SQLite + Alembic-Baseline.
- **Lieferung:** lauffähiges Grundgerüst, Backend ↔ Frontend verbunden.

### Stage 1 — Lokale Galerie (MVP, ohne ML)
- Single-/Bulk-Import, Content-Hash-Dedupe, Ablage in `Data/_unknown`.
- Thumbnail-Cache (`thumbnails.sqlite`), seitenweises Grid (Pagination), Detailansicht, Generierungs-Metadaten-Viewer.
- DB-Index (keine Sidecars), Sortierung nach Datum/Größe, Favoriten als physischer Move.
- **Papierkorb (Soft-Delete)** und Tastatur-Shortcuts (mit Legende).
- **Nutzbar als:** funktionierender lokaler Foto-Viewer mit Import und Durchsicht.

### Stage 2 — Klassifizierung & Suche (ohne Personen)
- Metadaten/EXIF/PNG-Chunks lesen → Quelle, Dimensionen, Framing-Heuristik, Qualität.
- WD14-Tagger (ONNX) für Auto-Tags + manuelle Tags; Florence-2-Captions; **CLIP/SigLIP-Embedding**.
- Modell-Registry + Konfigurationsseite mit **In-App-Download** (Queue, Hash-Prüfung, Gating), **frei wählbarem Modell-Ordner** und **In-Place-Einbindung vorhandener Dateien** für Core-ONNX-Modelle.
- Suche/Filter nach Tags, Klassifizierung, Quelle; Volltext über Captions; **semantische Suche**; **Tag-Verwaltung** (Merge/Alias/Bulk); **manuelle Tag-/Caption-Korrektur**; **Trigger-basierte Smart-Alben** (Person/Tag/Caption, automatisches Rein & Raus).
- **Nutzbar als:** durchsuchbare, getaggte und captionierte lokale Galerie.

### Stage 3 — Personen & Faces
- `buffalo_l`: Face-Detection + Extraktion mit Padding (nach `personX/faces/`), Embeddings.
- Auto-Clustering → Person-Ordner, `_unknown`-Handling, echte Kopien pro Person, `fixed_person` für manuell einsortierte Bilder.
- Manuelle Korrektur (Bild physisch verschieben), Top 10 disjunkte Personen + Score, **Merge/Split**, **Review-Queue**, Suche nach Person/Face.
- **Direkter Face-Import** (eigenständiges Face ohne Original).
- Duplikat-Suche innerhalb eines Person-Ordners inkl. prozentualer Ähnlichkeit.
- **Nutzbar als:** Galerie mit Personen-Gruppierung im Google-Fotos-Stil.

### Stage 4 — Bearbeitung (leichtgewichtig, ohne GPU)
- Crop (frei + fixe Ratios), **Smart-Crop auf Gesicht**, **Pad-to-Square/Aspect**, Drehen, Spiegeln, PNG/JPEG-Konvertierung, **Hintergrund-Entfernung (rembg)**.
- Versionierung: neue Version **nur bei bewusstem Speichern**; temporäre In-Session-Step-Historie. Re-Import editierter Bilder. Side-by-side-Vergleich.
- Edits/Upscales auch auf **Faces und bestehende Edits** anwendbar (Versionskette).
- Crop-Sonderfall (Person fällt heraus → kein Edit-Copy für diese Person, Original bleibt).
- Effiziente Neuverarbeitung: keine Re-Klassifizierung, nur Face-pHash-Dedupe auf neuen Versionen.
- **Nutzbar als:** vollständiger lokaler Editor für nicht-generative Operationen.

### Stage 5 — Generative Features (GPU, gated, optional)
- Generatives Backend (diffusers/ComfyUI), Varianten-Auswahl (fp16/fp8/GGUF) + **In-App-Download**.
- Upscale (SeedVR2/Flux2), Flux2-Edit (img2img) + Prompt-Templates, **Inpainting**.
- Optionale schwere Captioner (JoyCaption/Qwen-VL).
- **Nutzbar als:** vollständige Edit-Suite inkl. Upscale und generativer Edits.

### Stage 6 — Collections, Trainingssets & Export
- Alben/Collections, Gruppierung nach Original/Face/Edit-Lineage.
- Trainingssets mit Statistiken/Verteilung & Bucket-Stats, **Caption-Tools** (Trigger-Word/Prefix/Suffix/Find-Replace), **Near-Dupe-Vergleich (Links-Rechts, löschen)**, Train/Val-Split, Export mit Sidecar-`.txt` (Tags/Caption/beides).
- Alle Export-Workflows (Filter, Gruppierung, Favoriten nach Person, Zufalls-Favoriten distinct, Collections).
- **Nutzbar als:** vollständige Organisations- und Export-/Trainingsset-Pipeline.

### Querschnitt (parallel zu Stage 1–3) — Datensicherheit
- **DB-Backup-Export**, **FS↔DB-Reconciliation (Verify & Repair)** und **Thumbnail-/Face-Rebuild** — alles über die UI, manuell anstoßbar. Früh einziehen, da der Filesystem-Drop von Bildern (6.1a) Drift erzeugen kann.

---

## 19. Offene Punkte / Empfehlungen / Risiken

1. **DB als alleinige Wahrheit:** Keine Sidecars; alle Metadaten leben in der DB. Geht die DB verloren, sind Tags/Captions/Zuordnungen weg — die Bilddateien selbst bleiben in den Person-Ordnern erhalten. Dieses Risiko wird bewusst akzeptiert; ein regelmäßiges DB-Backup wird empfohlen.
2. **Echte Kopien:** Speicherbedarf steigt mit der Anzahl Personen pro Bild. Bei jedem Move (Favorit, manuelle Korrektur) wird die Datei physisch verschoben und der Pfad in der DB nachgeführt.
3. **`buffalo_l`-Lizenz:** Die Weights erfordern eine gesonderte Lizenz für kommerzielle Nutzung — daher beziehen statt mitliefern. Für privat/lokal unproblematisch.
4. **FLUX.2 klein 9B:** Non-Commercial-Lizenz und hoher VRAM-Bedarf (fp8/GGUF deutlich genügsamer). Für privaten Einsatz geeignet; kommerziell nicht.
5. **Crop-Sonderfall:** Fällt eine Person durch den Crop heraus, wird der Edit dieser Person nicht als Kopie zugeordnet; das Original mit der Person bleibt erhalten. Wird über die ohnehin laufende Face-Detection automatisch korrekt behandelt.
6. **Captioner auf reinem ONNX Runtime:** Florence-2 läuft auf onnxruntime, der Generierungs-Loop und Tokenizer sind selbst zu implementieren (oder `transformers` nur für den Tokenizer hinzuziehen) — das ist der aufwändigste Teil der ML-Schicht.
7. **Komponenten-Kompatibilität (Flux & Co.):** Beim In-Place-Einbinden von Komponenten-Modellen (Diffusion + Text-Encoder + VAE) können formal gültige, aber zueinander **inkompatible** Teile gewählt werden (z.B. falscher Text-Encoder oder eine VAE der falschen Familie). Das lädt zwar, liefert aber Matsch. **Empfehlung:** ein **Kompatibilitäts-Hinweis** (erwartete Encoder-/VAE-Familie je Diffusion-Modell aus dem Manifest), als **Warnung, nicht als hartes Gate** — der Nutzer behält die Freiheit, bewusst abzuweichen.
8. **Error-Handling & aussagekräftige Fehlermeldungen bei der Modellwahl:** Wird ein falsches/ungeeignetes Modell gewählt, darf die App **nicht stumm scheitern**. Jeder Fehler nennt **was erwartet wurde, was gefunden wurde und den nächsten Schritt** — siehe Fehlerklassen in 12.2a.

---

*Stand: Konzeptentwurf. Datenmodell und API sind als Grundlage gedacht und werden in der Umsetzung verfeinert.*
