# Photofant — Agent Hub

🚧 Aktive Arbeit → STATE.md

Lokale, private Bildverwaltung („vergisst nie"): Galerie, Personen-Erkennung, Tagging/Captioning, semantische Suche, Editor, generative Bearbeitung (Upscale/Flux/Inpaint) inkl. ComfyUI-Anbindung, Trainingssets. Zur Laufzeit vollständig offline.

## Code finden — erst hier, dann greppen

[docs/code-map.md](docs/code-map.md) bildet **Feature → Dateien** über Frontend + Backend ab. Bevor du Grep/Glob über die Codebase laufen lässt: dort nachschlagen. Die Namen laufen parallel — `features/<x>/` · `store/<x>/` · `services/<x>.service.ts` · `api/<x>.py` · `jobs/<x>_job.py`. Routen-Details: [docs/routes.md](docs/routes.md), DB-Felder: [docs/models.md](docs/models.md).

## Einstieg (in dieser Reihenfolge lesen)

1. [docs/PROJECT.md](docs/PROJECT.md) — Ziel, Scope, Stack, Stand
2. [docs/code-map.md](docs/code-map.md) — Feature → Dateien (Navigations-Index)
3. [docs/Konzept-Photofant.md](docs/Konzept-Photofant.md) — Voll-Spezifikation (Datenmodell, API, Pipeline, Modelle); bei Widerspruch gewinnt das Konzept
4. [docs/design/README.md](docs/design/README.md) — UI-Referenz; die HTML-Prototypen in `docs/design/` sind High-Fidelity, Pixel-Treue ist das Ziel

## Stack

| Layer | Choice |
|---|---|
| Frontend | Angular 19.2 + Tailwind v4 (Tokens) + NgRx 19 classic |
| Backend | Python + FastAPI + Uvicorn |
| DB | SQLite + Alembic, `sqlite-vec` |
| Inferenz | ONNX Runtime (Core) · torch/transformers (Heavy Captioners: JoyCaption, Qwen-VL) · ComfyUI (einziger Generativ-Pfad: Upscale/Edit/Inpaint + Fire-and-Forget; ADR-003, ADR-008) |
| Pakete | `uv` (Backend) · `npm` (Frontend) |

## Konventionen

| Thema | Datei |
|---|---|
| Commits | [docs/conventions/commits.md](docs/conventions/commits.md) |
| Linting | [docs/conventions/linting.md](docs/conventions/linting.md) |
| Testing | [docs/conventions/testing.md](docs/conventions/testing.md) |
| Python | [docs/conventions/python.md](docs/conventions/python.md) |
| TypeScript | [docs/conventions/typescript.md](docs/conventions/typescript.md) |
| Angular | [docs/conventions/angular.md](docs/conventions/angular.md) |
| NgRx | [docs/conventions/ngrx.md](docs/conventions/ngrx.md) |

## Planung

- Aktive Pläne (Backlog): `docs/planning/` — siehe STATE.md für die vollständige, aktuelle Liste
- Entscheidungen (ADRs): `docs/decisions/` (001–003, 004–006, 008)
- Archiv (umgesetzte Pläne): `docs/archive/`
- [Design-Reconciliation](docs/design-reconciliation.md) — View-für-View-Abgleich Mockup vs. Impl

## CI

Vor jedem Commit mit Code-Änderungen — einzeln ausführen:

```
cd backend && uv run ruff check .
cd frontend && npm run lint && npm run build
```

## Critical Rules

1. **Zur Laufzeit kein Netzwerkverkehr** — einzige Ausnahme: Modell-Downloads über die Settings-UI.
2. **Keine Sidecar-Dateien** — Metadaten ausschließlich in der DB; Person-Ordner enthalten nur Bilddateien.
3. **Schwere Verarbeitung genau einmal pro Content-Hash** (`processing_ledger`).
4. **Keine Modell-Binaries im Repo** — Bezug nur über die Settings-UI oder In-Place-Einbindung.
5. **Die UI blockiert nie** — alles Langsame läuft über die Job-Queue.
6. **Nach Code-Änderungen zugehörige Tests laufen lassen**, Failures fixen.
7. **Tunable Parameter gehören in `settings.json`** — Schwellwerte, Timeouts, Größen und andere einstellbare Werte werden nie als Modul-Konstante oder Magic Number hardcoded. Im Planungsschritt melden, welche Keys angelegt werden sollen; Sascha entscheidet dann, bevor die Phase läuft. Ausnahme: modell-interne Architekturparameter (Tensorformen, Strides, Canvas-Größen), die fest mit dem Modell-Design zusammenhängen.
