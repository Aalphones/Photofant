# Photofant — Kontext

> Destillat für Planung und Einstieg. Die vollständige Spezifikation (Datenmodell, API, Pipeline, Modell-Management) steht in [Konzept-Photofant.md](Konzept-Photofant.md) — bei Widerspruch gewinnt das Konzept.

## Ziel & Vision

Photofant („vergisst nie") ist eine lokal laufende, private Foto-Verwaltung nach Google-Fotos-Vorbild für eigene Bildsammlungen — insbesondere KI-generierte und fotografische Assets. Bilder werden einmalig verarbeitet (Gesichter, Tags, Captions, Embeddings), pro Person als echte Kopie im Dateisystem abgelegt und sind danach vollständig durchsuchbar. Zur Laufzeit findet kein Netzwerkverkehr statt; Single-User, keine Authentifizierung.

## Scope

- **Galerie:** Import (Single/Bulk/FS-Scan), justiertes Grid mit Pagination, Lightbox, Favoriten (physischer Move), Papierkorb, Shortcuts.
- **Klassifizierung & Suche:** EXIF/PNG-Metadaten, WD14-Tags, Florence-2-Captions, CLIP/SigLIP-Embeddings; Suche über Tags, Caption-Volltext und semantisch; Tag-Verwaltung (Merge/Alias); Smart-Alben mit Triggern (Person/Tag/Caption).
- **Personen:** Face-Detection/-Recognition (`buffalo_l`), Auto-Clustering, Review-Queue, Merge/Split, manuelle Korrektur mit physischem Move, direkter Face-Import.
- **Bearbeitung:** Crop/Rotate/Mirror/Convert/rembg (CPU), Upscale + Flux-Edit + Inpainting (GPU, gated), Versionierung mit bewusstem Speichern.
- **Trainingssets & Export:** Statistiken, Caption-Tools, Near-Dupe-Vergleich, Train/Val-Split, Sidecar-`.txt`-Export.
- **Wartung:** DB-Backup, FS↔DB-Reconciliation, Thumbnail-/Face-Rebuild — alles über die UI.
- **Modell-Management:** In-App-Download oder In-Place-Einbindung vorhandener Dateien, Varianten je VRAM, Feature-Gating.

## Nicht-Ziele

- Keine NSFW-, Stil- oder automatische Outfit-Klassifizierung.
- Kein Multi-User, keine Authentifizierung, kein Cloud-Sync, keine Internetdienste zur Laufzeit.
- Keine Sidecar-Metadaten im Dateisystem (DB ist alleinige Wahrheit; Verlust-Risiko bewusst akzeptiert).
- Keine Modell-Binaries im Repository.

## Stack

| Layer | Choice |
|---|---|
| Frontend | Angular (aktuelles Major, bei Stage 0 pinnen) |
| Styling | Tailwind CSS v4 als Token-Quelle (`@theme`), BEM + komponenten-scoped SCSS |
| State | NgRx classic (Store/Effects/Entity) für Server-State, Signals lokal |
| Backend | Python + FastAPI + Uvicorn |
| DB | SQLite + Alembic, `sqlite-vec` für Vektorsuche |
| Inferenz Core | ONNX Runtime (`buffalo_l`, WD14, Florence-2, CLIP/SigLIP, rembg) |
| Inferenz generativ | torch/diffusers oder ComfyUI-Backend (gated, optional) |
| Paketverwaltung | `uv` (Backend), `npm` (Frontend) |

Begründungen: Angular + NgRx ist die Konzept-Entscheidung (Sektion 15 ist darauf ausgelegt); die React-Prototypen in `docs/design/` dienen nur als visuelle Referenz. Tailwind liefert die Design-Tokens, die Prototyp-CSS (`docs/design/styles.css`) ist deren kanonische Quelle.

## Constraints

- **Offline-Garantie:** Modell-Downloads nur über die Settings-UI; danach `HF_HUB_OFFLINE=1` bei torch-Modellen.
- **Windows-first:** `install.cmd`/`start.cmd` zusätzlich zu `.sh`; Entwicklung auf Windows 11.
- **Lizenz-Grenzen:** `buffalo_l`-Weights und FLUX.2 sind non-commercial — beziehen statt mitliefern, rein private Nutzung.
- **UI blockiert nie:** Alles potenziell Langsame läuft über die In-Process-Job-Queue (SSE-Fortschritt).
- **GPU optional:** Core-Features laufen notfalls auf CPU; generative Features sind vollständig gated.

## Meilensteine (Plan-Backlog)

Vollständig ausgeplant in `docs/planning/` — Umsetzung in dieser Reihenfolge, Abweichungen unten vermerkt:

| # | Plan | Stage | Hängt ab von |
|---|---|---|---|
| P1 | [Stage-0-Fundament](planning/2026-06-12_p01-stage0-fundament/README.md) | 0 | — |
| P2 | [Galerie-MVP](planning/2026-06-12_p02-galerie-mvp/README.md) | 1 | P1 |
| P3 | [Datensicherheit](planning/2026-06-12_p03-datensicherheit/README.md) | Querschnitt | P2 |
| P4 | [Modell-Management](planning/2026-06-12_p04-modell-management/README.md) | 2a | P1 (parallel zu P2/P3 möglich) |
| P5 | [Klassifizierung](planning/2026-06-12_p05-klassifizierung/README.md) | 2b | P2, P4 |
| P6 | [Suche & Alben](planning/2026-06-12_p06-suche-und-alben/README.md) | 2c | P5 |
| P7 | [Personen & Faces](planning/2026-06-12_p07-personen/README.md) | 3 | P2, P4 |
| P8 | [Editor CPU](planning/2026-06-12_p08-editor-cpu/README.md) | 4 | P2, P4 — **vor P7 vorziehbar** |
| P8b | [ComfyUI-Integration](planning/2026-06-15_p08b-comfyui-integration/README.md) | 5 | P2, P4, P8 — **koexistiert mit P9**, optional/parkbar |
| P9 | [Generativ (in-process)](planning/2026-06-12_p09-generativ/README.md) | 5 | P8 — **optional/parkbar** |
| P10 | [Trainingssets & Export](planning/2026-06-12_p10-trainingssets-export/README.md) | 6 | P5, P6 |

Scope-Abweichung vom Konzept: Komponenten-Modelle (Flux) + VRAM-Matrix sind von Stage 2 nach P9 verschoben (gebraucht erst dort); Framing-Heuristik liefert P7 nach (braucht Face-BBox).

## Offene Fragen

- Generatives Backend: **diffusers oder ComfyUI?** → ADR-002 (P9 Phase 1) bleibt für den in-process-Pfad; der **koexistierende ComfyUI-Trigger-Pfad** (Fire-and-Forget) wird separat in **P8b** umgesetzt und in ADR-003 dokumentiert.
- Vektorsuche: **`sqlite-vec` oder FAISS?** → wird als ADR-001 in P5 Phase 4 entschieden (Spike, Default-Empfehlung `sqlite-vec`).
- Angular-Major und Test-Runner → werden in P1 gepinnt.
