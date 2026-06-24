# Photofant — Kontext

> Destillat für Planung und Einstieg. Die vollständige Spezifikation (Datenmodell, API, Pipeline, Modell-Management) steht in [Konzept-Photofant.md](Konzept-Photofant.md) — bei Widerspruch gewinnt das Konzept.

## Ziel & Vision

Photofant („vergisst nie") ist eine lokal laufende, private Foto-Verwaltung nach Google-Fotos-Vorbild für eigene Bildsammlungen — insbesondere KI-generierte und fotografische Assets. Bilder werden einmalig verarbeitet (Gesichter, Tags, Captions, Embeddings), pro Person als echte Kopie im Dateisystem abgelegt und sind danach vollständig durchsuchbar. Zur Laufzeit findet kein Netzwerkverkehr statt; Single-User (optionales lokales Passwort-Schloss, kein Multi-User).

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
- Kein Multi-User, keine Benutzerkonten, kein Cloud-Sync, keine Internetdienste zur Laufzeit. (Ein **optionales lokales Passwort-Schloss** — ein Passwort, Unlock-Screen — ist eingebaut; das ersetzt kein Multi-User-Auth.)
- Keine Sidecar-Metadaten im Dateisystem (DB ist alleinige Wahrheit; Verlust-Risiko bewusst akzeptiert).
- Keine Modell-Binaries im Repository.

## Stack

| Layer | Choice |
|---|---|
| Frontend | Angular 19.2 |
| Styling | Tailwind CSS v4 als Token-Quelle (`@theme`), BEM + komponenten-scoped SCSS |
| State | NgRx classic (Store/Effects/Entity) für Server-State, Signals lokal |
| Backend | Python + FastAPI + Uvicorn |
| DB | SQLite + Alembic, `sqlite-vec` für Vektorsuche |
| Inferenz Core | ONNX Runtime (`buffalo_l`, WD14, Florence-2, CLIP/SigLIP, rembg) |
| Inferenz generativ | torch/diffusers (in-process, ADR-002) **und** ComfyUI-Trigger (ADR-003) — beide gated/optional |
| Paketverwaltung | `uv` (Backend), `npm` (Frontend) |

Begründungen: Angular + NgRx ist die Konzept-Entscheidung (Sektion 15 ist darauf ausgelegt); die React-Prototypen in `docs/design/` dienen nur als visuelle Referenz. Tailwind liefert die Design-Tokens, die Prototyp-CSS (`docs/design/styles.css`) ist deren kanonische Quelle.

## Constraints

- **Offline-Garantie:** Modell-Downloads nur über die Settings-UI; danach `HF_HUB_OFFLINE=1` bei torch-Modellen.
- **Windows-first:** `install.cmd`/`start.cmd` zusätzlich zu `.sh`; Entwicklung auf Windows 11.
- **Lizenz-Grenzen:** `buffalo_l`-Weights und FLUX.2 sind non-commercial — beziehen statt mitliefern, rein private Nutzung.
- **UI blockiert nie:** Alles potenziell Langsame läuft über die In-Process-Job-Queue (SSE-Fortschritt).
- **GPU optional:** Core-Features laufen notfalls auf CPU; generative Features sind vollständig gated.

## Stand & Meilensteine

Code-Einstieg pro Feature: [code-map.md](code-map.md). Umgesetzte Pläne liegen in `docs/archive/2026-06/`, offene im Backlog `docs/planning/`.

**Umgesetzt:**

| Stage | Feature |
|---|---|
| 0 | Fundament — Backend- + Frontend-Skeleton, CI |
| 1 | Galerie-MVP — Import (Single/Bulk/FS-Scan), Grid, Lightbox, Favoriten, Papierkorb, Shortcuts |
| Querschnitt | Datensicherheit — DB-Backup, FS↔DB-Reconciliation, Rebuild |
| 2a | Modell-Management — Download/In-Place, VRAM-Varianten, Feature-Gating |
| 2b | Klassifizierung — WD14-Tags, Florence-2-Captions, CLIP-Embeddings, Heuristik-Pipeline |
| 2c | Suche & Alben — Tag/Caption/semantische Suche, Tag-Verwaltung, Smart-Alben |
| 3 | Personen & Faces — `buffalo_l`, Clustering, Review-Queue, Merge/Split, Face-Import |
| 4 | Editor (CPU) — Crop/Rotate/Mirror/Convert/rembg, Versionierung |
| 5 | Generativ — Upscale, Flux-Edit, Inpainting; schwere Captioner (Qwen2.5-VL, JoyCaption) |
| 5 | ComfyUI-Trigger-Integration — Verbindung, Workflow-Registry, Run-Leiste, Import |
| — | Einstellungen-Shell, `settings.json`-Infrastruktur, Duplikaterkennung (pHash), konfigurierbare Face-Parameter, Design-Angleichung |

**Backlog** (`docs/planning/`):

| Plan | Inhalt |
|---|---|
| P10 | Trainingssets & Export — Statistiken, Caption-Tools, Train/Val-Split, Sidecar-`.txt`-Export |
| P11 | Duale Duplikaterkennung — zweites Verfahren neben pHash |
| P13 | Person-Bulk-Import |

## Entscheidungen

Architektur-Fragen sind als ADRs entschieden — Details in `docs/decisions/`:

- **ADR-001** Vektor-Backend → `sqlite-vec`
- **ADR-002** Generatives Backend → torch/diffusers in-process
- **ADR-003** ComfyUI-Trigger-Integration (koexistiert mit ADR-002)
- **ADR-004** Einstellungen-Shell (Master-Detail)
- **ADR-005** Tag-Verwaltung in den Einstellungen verortet
- **ADR-006** pHash-Duplikaterkennung
