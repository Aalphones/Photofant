# Phase 2 — Finden & Ansehen (Read-Tools inkl. Bild-Content)

**Komplexität:** standard · **Status:** pending

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

- [ ] `tools/library.py` registriert diese Tools, alle über `adapter.run_endpoint`:
  - [ ] `search_photos(query?, mode?, tags?, person_id?, classification?, source?, quality_min?, framing?, favourite?, sort?, order?, page?, page_size?)`
        → deckt `list_assets` samt aller Filter/`q_mode` ab; Ergebnis gedeckelt auf `mcp.max_search_results`,
        gibt `items` (id, hash, res, source, caption-kurz, tags-namen, favourite) + `total` + `facets` zurück.
  - [ ] `get_photo(asset_id)` → `AssetDetailDto` als knappes JSON (Tags, Caption, Faces, Klassifizierung,
        Versionen, Pfad, Qualität, Framing).
  - [ ] `view_photo(asset_id)` → MCP-`ImageContent`, JPEG in `mcp.thumbnail_size`, **genau ein Bild**.
        Bei `mcp.return_images=false`: kein Bild, stattdessen Text „Bild-Rückgabe ist deaktiviert".
  - [ ] `list_facets(...)` → verfügbare Tags/Personen/Kategorien/Framings/Sources mit Zählern (aus
        `list_assets`-`facets`, ohne Item-Liste) — der Überblick, was es zu filtern gibt.
  - [ ] `find_similar(asset_id, limit?)` → CLIP-ähnliche Bilder (`SimilarAssetDto`).
  - [ ] `get_lineage(asset_id)` → Versions-/Ableitungs-Baum (`LineageDto`).
  - [ ] `get_capabilities()` → welche Modelle aktiv sind (faces/tagging/captioning/semantic/rembg/heavy).
  - [ ] `list_persons()` → Personen mit Namen/Gruppe/Count/Portrait-Face-ID (Read; Verwaltung in Phase 4).
- [ ] Job-Verfolgung:
  - [ ] `get_job_status(job_id)` → Status/Fortschritt/Fehler eines Jobs.
  - [ ] `list_jobs(state?)` → laufende/fertige Jobs (Deckel wie oben).
- [ ] Jedes Tool hat eine präzise Docstring/Description (der Agent wählt Tools danach); destruktiv: keins.

## Umsetzung — Checkliste

- [ ] `tools/library.py` mit den Tools oben, registriert an `mcp_server` aus Phase 1.
- [ ] `view_photo`: Thumbnail über die bestehende Thumbnail-Erzeugung (`media/thumbnails.py` bzw.
      `get_thumbnail`-Pfad), als `ImageContent` verpacken; `return_images`/`thumbnail_size` respektieren.
- [ ] `get_job_status`/`list_jobs` gegen `jobs/queue.py` (Poll, kein SSE).
- [ ] Doc: `docs/routes.md` MCP-Abschnitt um die Read-Tools ergänzen.

## Report-Back
