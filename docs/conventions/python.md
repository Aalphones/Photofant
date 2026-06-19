# Python Conventions — Photofant

> **Stack** (pinned for this project):
> | Layer | Choice |
> |---|---|
> | Python | 3.12+ (bei Stage 0 exakt pinnen) |
> | Framework | FastAPI + Uvicorn |
> | DB | SQLite + Alembic |
> | Pakete | `uv` mit Lockfile |
>
> **Builds on user-level baseline.** Project overrides below take precedence.

## Package Management

- **`uv`** für alle Operationen (`uv venv`, `uv sync`, `uv add`)
- `uv` selbst über den Standalone-Installer von astral.sh beziehen — nicht via pip
- Dependencies gepinnt über Lockfile; `onnxruntime` ist Pflicht-Dependency, torch/diffusers nur als optionale Extra-Gruppe (generative Features)

## Windows

- Volle absolute Pfade: `C:/path/to/.venv/Scripts/python.exe -m pytest tests/ -v`

## Types

- Alle Funktionsparameter und Returns annotiert, auch private Helpers
- Moderne Syntax: `list[str]`, `dict[str, int]`, `X | None`
- `TypedDict` für Dict-Shapes; `pydantic` für API-Modelle (FastAPI-Standard); `Protocol` für strukturelle Typen (z.B. Inferenz-Engine-Interfaces)

## Style

- Beschreibende Namen; `if/elif/else` statt verschachtelter Ternaries
- `enum.StrEnum` statt Magic Strings (z.B. `source`, `framing`, `caption_mode`)
- F-Strings, nie `%`-Formatting
- `pathlib` statt `os.path`

## Imports

- stdlib → third-party → lokal, durch Leerzeilen getrennt
- **Nur absolute Imports** — `from photofant.db.client import …`, nie relativ
- Kein `from x import *`
- Type-only Imports in `if TYPE_CHECKING:`-Blöcken

## Robustness

- **Externe I/O** (Dateisystem-Operationen, Modell-Downloads, Inferenz) immer in `try/except` mit spezifischen Exception-Typen — loggen + degradieren statt crashen; Nutzer-Meldungen nach dem Muster „erwartet · gefunden · nächster Schritt" (Konzept 12.2a)
- **Niemals Credentials/Tokens loggen**
- **Unterbrechbare Delays:** `asyncio.sleep()` in async Code, `Event.wait(timeout)` in Threads — nie `time.sleep()` (blockiert sauberen Shutdown der Job-Queue)

## SQLite

- SQLite speichert **nur naive Datetimes**. Projekt-Strategie: **UTC, naiv gespeichert** —
  ```python
  datetime.now(timezone.utc).replace(tzinfo=None)
  ```
  Überall, ohne Ausnahme.
- Schema-Änderungen ausschließlich über Alembic-Migrationen, nie ad-hoc `ALTER TABLE`

## Errors

- Spezifische Exception-Klassen raisen, schmalste passende Exception catchen
- Nie still schlucken — loggen + re-raisen oder begründen
- API-Fehler als strukturierte Codes (`MODEL_WRONG_ROLE`, `MODEL_INCOMPLETE`, …), das Frontend mappt auf Meldungen

## Versionierung

- **Einzige Pflege-Stelle:** `pyproject.toml` `[project] version`
- **Lesen zur Laufzeit:** `importlib.metadata.version("photofant-backend")`
- **Fallback für Direktstart** ohne `uv run`/install: `PackageNotFoundError` fangen, `"dev"` zurückgeben
- **Keine `VERSION = "..."` Konstante** in irgendeiner Python-Datei — weder in `health.py` noch anderswo
  ```python
  from importlib.metadata import PackageNotFoundError, version
  try:
      _APP_VERSION = version("photofant-backend")
  except PackageNotFoundError:
      _APP_VERSION = "dev"
  ```

## Critical Rules

1. **Kein Netzwerkzugriff zur Laufzeit** außer dem Download-Job der Settings-UI — `HF_HUB_OFFLINE=1`/`TRANSFORMERS_OFFLINE=1` sobald torch-Modelle aktiv sind.
2. **Datei-Moves und DB-Update gehören zusammen** — jede physische Verschiebung führt den Pfad in der DB nach, kein Zustand dazwischen, der bei Crash verwaist.
3. **Schwerverarbeitung idempotent über Content-Hash** — vor jedem Job den `processing_ledger` prüfen.
4. **`mypy --strict` und `ruff` grün** für neuen Code.
