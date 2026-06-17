# Photofant — Agent Hub

🚧 Aktive Arbeit → STATE.md

Lokale, private Bildverwaltung („vergisst nie"): Galerie, Personen-Erkennung, Tagging/Captioning, semantische Suche, Editor, Trainingssets. Zur Laufzeit vollständig offline.

## Einstieg (in dieser Reihenfolge lesen)

1. [docs/PROJECT.md](docs/PROJECT.md) — Ziel, Scope, Stack, Meilensteine
2. [docs/Konzept-Photofant.md](docs/Konzept-Photofant.md) — Voll-Spezifikation (Datenmodell, API, Pipeline, Modelle); bei Widerspruch gewinnt das Konzept
3. [docs/design/README.md](docs/design/README.md) — UI-Referenz; die HTML-Prototypen in `docs/design/` sind High-Fidelity, Pixel-Treue ist das Ziel

## Stack

| Layer | Choice |
|---|---|
| Frontend | Angular 19.2 + Tailwind v4 (Tokens) + NgRx 19 classic |
| Backend | Python + FastAPI + Uvicorn |
| DB | SQLite + Alembic, `sqlite-vec` |
| Inferenz | ONNX Runtime (Core) · torch/diffusers (generativ, gated) |
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

- Aktive Pläne: `docs/planning/` (Meilensteine aus PROJECT.md sind die Phasen-Kandidaten)
- Entscheidungen (ADRs): `docs/decisions/`
- Archiv: `docs/archive/`

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
