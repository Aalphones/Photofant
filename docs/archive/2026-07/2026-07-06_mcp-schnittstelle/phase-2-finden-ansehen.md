# Phase 2 — Finden & Ansehen (Read-Tools inkl. Bild-Content)

**Komplexität:** standard · **Status:** complete

## Kontext (vor dem Bauen lesen)

- `README.md` — Kontrakt (Rückgabe-Format, Bild-Regel, Job-Regel), settings-Keys.
- `phase-1-infrastruktur-settings.md` — das etablierte Muster (`server.py`, `adapter.py`, Tool-Registrierung).
- `backend/photofant/api/assets.py` — `list_assets` (alle Filter/`q_mode`), `get_asset` (AssetDetailDto),
  `get_thumbnail`, `get_lineage`.
- `backend/photofant/api/review.py` — `GET /assets/{id}/similar` (`find_similar`).
- `backend/photofant/api/models.py` — `GET /models/capabilities` (`get_capabilities`).
- `backend/photofant/api/jobs.py` — `GET /jobs/stream` (SSE). **Für MCP wird gepollt, nicht gestreamt**:
  `jobs/queue.py` bietet den Job-Status im Speicher — dort die Lese-Funktion für `get_job_status`/`list_jobs`
  finden (Muster: wie der Stream seine Job-Objekte zieht).
- `docs/routes.md` — Abschnitte „Assets", „Semantische Suche", „Faces gallery", DTO-Definitionen.

## AK (falsifizierbar)

- [x] `tools/library.py` registriert diese Tools, alle über `adapter.run_endpoint`:
  - [x] `search_photos(query?, mode?, tags?, person_id?, classification?, source?, quality_min?, framing?, favourite?, sort?, order?, page?, page_size?)`
        → deckt `list_assets` samt aller Filter/`q_mode` ab; Ergebnis gedeckelt auf `mcp.max_search_results`,
        gibt `items` (id, hash, res, source, caption-kurz, tags-namen, favourite) + `total` + `facets` zurück.
  - [x] `get_photo(asset_id)` → `AssetDetailDto` als knappes JSON (Tags, Caption, Faces, Klassifizierung,
        Versionen, Pfad, Qualität, Framing).
  - [x] `view_photo(asset_id)` → MCP-`ImageContent`, JPEG in `mcp.thumbnail_size`, **genau ein Bild**.
        Bei `mcp.return_images=false`: kein Bild, stattdessen Text „Bild-Rückgabe ist deaktiviert".
  - [x] `list_facets(...)` → verfügbare Tags/Personen/Kategorien/Framings/Sources mit Zählern (aus
        `list_assets`-`facets`, ohne Item-Liste) — der Überblick, was es zu filtern gibt.
  - [x] `find_similar(asset_id, limit?)` → CLIP-ähnliche Bilder (`SimilarAssetDto`).
  - [x] `get_lineage(asset_id)` → Versions-/Ableitungs-Baum (`LineageDto`).
  - [x] `get_capabilities()` → welche Modelle aktiv sind (faces/tagging/captioning/semantic/rembg/heavy).
  - [x] `list_persons()` → Personen mit Namen/Gruppe/Count/Portrait-Face-ID (Read; Verwaltung in Phase 4).
- [x] Job-Verfolgung:
  - [x] `get_job_status(job_id)` → Status/Fortschritt/Fehler eines Jobs.
  - [x] `list_jobs(state?)` → laufende/fertige Jobs (Deckel wie oben).
- [x] Jedes Tool hat eine präzise Docstring/Description (der Agent wählt Tools danach); destruktiv: keins.

## Umsetzung — Checkliste

- [x] `tools/library.py` mit den Tools oben, registriert an `mcp_server` aus Phase 1.
- [x] `view_photo`: Thumbnail über die bestehende Thumbnail-Erzeugung (`media/thumbnails.py` bzw.
      `get_thumbnail`-Pfad), als `ImageContent` verpackt; `return_images`/`thumbnail_size` respektiert.
- [x] `get_job_status`/`list_jobs` gegen `jobs/queue.py` (Poll, kein SSE).
- [x] Doc: `docs/routes.md` MCP-Abschnitt um die Read-Tools ergänzt.

## Report-Back

**Umgesetzt:** `backend/photofant/mcp/tools/library.py` (neu) mit 10 Read-Tools, registriert über
`server.py`-Import (`from photofant.mcp.tools import library  # noqa: E402,F401`, nach der
`mcp_server`-Definition — vermeidet Zirkelimport). Alle Tools rufen die bestehenden
`api/*.py`-Funktionen (`list_assets`, `get_asset`, `get_asset_thumbnail`, `get_asset_lineage`,
`get_similar_assets`, `list_persons`) über `run_endpoint()`/`db_session()`; `get_job_status`/
`list_jobs` lesen `jobs/queue.py:job_queue.snapshot()` direkt (kein REST-Pendant, kein
DB-Zugriff nötig); `get_capabilities` ruft den (synchronen) Endpoint direkt statt über
`run_endpoint()`.

`search_photos`/`list_facets` reichern die knappe Projektion pro Asset um Caption (gekürzt auf
140 Zeichen) und Tag-Namen an — dafür zwei gebatchte Zusatz-Queries innerhalb derselben Session
(kein N+1), da `AssetDto` (im Gegensatz zu `AssetDetailDto`) diese Felder nicht mitführt.
`view_photo` snappt `mcp.thumbnail_size` (freies Zahlenfeld 64–1024) auf die vom Thumbnail-Endpoint
erlaubte nächstgelegene Größe {256,512,1024}.

ruff + mypy grün. Smoke-Test (ad-hoc, gegen die echte lokale DB, kein Server-Neustart nötig):
alle 10 Tools durchlaufen, `search_photos`/`get_photo`/`view_photo`/`find_similar`/`get_lineage`/
`get_capabilities`/`list_persons`/`list_facets`/`list_jobs`/`get_job_status` liefern plausible
Ergebnisse gegen ein reales Asset; `view_photo` liefert reale JPEG-Bytes.

**Findings für spätere Phasen:** synchrone Endpoints brauchen direkten Aufruf statt
`run_endpoint()`; Tools mit Nicht-Pydantic-Rückgabetyp (`Image`) brauchen
`@mcp_server.tool(structured_output=False)`, sonst crasht die Registrierung.
