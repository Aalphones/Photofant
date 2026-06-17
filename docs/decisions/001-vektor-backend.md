# ADR-001 — Vektor-Backend für semantische Suche

> Status: **akzeptiert** · Datum: 2026-06-17 · Kontext: P5 Phase 4 (CLIP-Embeddings & Vektor-Index)

## Kontext

Die semantische Suche („mehr wie dieses", Text→Bild) braucht einen Vektor-Index für
CLIP-Embeddings (768-dim, float32, L2-normiert). Erwartete Größenordnung laut Konzept
(§16): bis ~100k Vektoren auf einem lokalen Single-User-Rechner unter Windows. Photofant
ist offline-first, hält den gesamten Zustand in **einer** SQLite-Datei
(`.photofant/db.sqlite`) und vermeidet zur Laufzeit Netzwerkzugriff und schwere Runtimes.

Zwei Kandidaten:

- **sqlite-vec** — SQLite-Loadable-Extension (`vec0`-Virtual-Table). Index lebt **in
  derselben DB-Datei**, kein Zusatzprozess, kein separater Index auf Platte.
- **FAISS** — eigenständige C++/Python-Bibliothek mit separater Index-Datei, die zur
  Laufzeit geladen und bei Schreibzugriff zurückgeschrieben werden muss.

## Entscheidung

**sqlite-vec.** Bestätigt durch einen kurzen Spike auf der Zielplattform (Windows 10,
CPython 3.12), nicht nach Gefühl:

- `sqlite3.Connection.enable_load_extension` ist im mitgelieferten CPython **verfügbar**.
- `pip`/`uv`-Wheel `sqlite-vec==0.1.9` lädt sauber, `vec_version()` antwortet.
- `vec0`-Virtual-Table mit `distance_metric=cosine` liefert korrekte KNN-Ergebnisse
  (Query [1,0,0] → Treffer nach aufsteigender Cosine-Distanz sortiert).

## Begründung (Kriterien aus dem Plan)

| Kriterium | sqlite-vec | FAISS |
|---|---|---|
| Eine Datei vs. Zusatz-Index | ✅ Index in `db.sqlite` | ❌ separate `.faiss`-Datei, Sync-Pflicht |
| Persistenz | ✅ implizit (DB-Tabelle, übersteht Neustart) | ⚠️ manuelles Schreiben/Laden, Crash-Drift möglich |
| Windows-Wheels | ✅ vorhandenes Wheel, lädt | ⚠️ `faiss-cpu` Windows-Wheels historisch wackelig |
| Transaktion mit Metadaten | ✅ gleiche Connection/Transaktion wie ORM-Writes | ❌ getrennter Zustand, Zwei-Phasen-Problem |
| Performance @ ~100k | ✅ brute-force exakt, für 100k×768 lokal ausreichend | ✅ (ANN, erst bei Millionen relevant) |

Bei der erwarteten Größenordnung ist der exakte Brute-Force-Scan von `vec0` schnell genug;
die ANN-Stärke von FAISS spielt erst jenseits dieses Bereichs eine Rolle und rechtfertigt
den zweiten Persistenz-Mechanismus nicht.

## Konsequenzen

- Neue Pflicht-Dependency: `sqlite-vec`.
- Die Extension wird **pro Connection** geladen — zentral via SQLAlchemy-`connect`-Event
  (`photofant/db/engine.py`) und in der Migration (auf `op.get_bind()`), die den
  `vec0`-Table anlegt. Helper: `photofant/db/vector_index.py:load_vec_extension`.
- Source of Truth bleibt `asset.clip_embedding` (BLOB, float32-Bytes). Der `vec0`-Table
  ist ein **rekonstruierbarer** Index (rowid = `asset.id`); `rebuild_index()` baut ihn aus
  den BLOBs neu — Drift zwischen BLOB und Index ist damit vorwärts-heilbar.
- Cosine-Score = `1 − Distanz` (vec0 liefert Cosine-Distanz bei `distance_metric=cosine`).

## Verworfene Alternative

FAISS — würde einen zweiten Persistenz-/Sync-Mechanismus neben SQLite einführen
(separate Index-Datei, eigenes Lade-/Schreibmodell, eigenes Crash-Verhalten) ohne
spürbaren Nutzen in der Zielgrößenordnung. Wieder aufgreifen, falls der Bestand die
100k-Marke deutlich überschreitet und exakte Scans zu langsam werden.
