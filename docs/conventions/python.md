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
- **Kein blockierendes I/O im Event-Loop.** `async def` macht blockierende Arbeit im Funktionskörper nicht sicher — ein blockierender DB-Call, `requests.*`, Datei-I/O, PIL/Bild-Encoding oder `hashlib` über große Daten legt den *gesamten* Loop lahm, inklusive aller anderen Requests/Jobs im Prozess. Auslagern via `asyncio.to_thread(fn, ...)` bzw. `loop.run_in_executor(pool, fn, ...)` — Pattern wird im Projekt bereits breit genutzt (Jobs, API-Routen), hier nur nachdokumentiert.

## SQLite

- SQLite speichert **nur naive Datetimes**. Projekt-Strategie: **UTC, naiv gespeichert** —
  ```python
  datetime.now(timezone.utc).replace(tzinfo=None)
  ```
  Überall, ohne Ausnahme. **Bewusste Abweichung von der User-Baseline** (die aware UTC via `DateTime(timezone=True)` empfiehlt): Entscheidung stand schon vor dieser Doku-Ergänzung im Code, wird hier nur nachträglich begründet festgehalten — nicht rückwirkend anfassen, konsistent bleiben ist wichtiger als die "bessere" Variante nachzuziehen.
- Schema-Änderungen ausschließlich über Alembic-Migrationen, nie ad-hoc `ALTER TABLE`
- **Filter-Spalten kriegen ihren Index im selben Change — nie "später".** Jede Spalte in `.filter()`/`.where()`/`order_by`/Joins (Enum-/Status-Spalten, FKs, Lookup-IDs) bekommt ihren Index, sobald Spalte oder Query eingeführt wird — deklariert sowohl im Model (`index=True` bzw. `__table_args__`) als auch in der Migration. SQLite indiziert automatisch nur PK/UNIQUE — FK-Spalten bekommen von sich aus nichts, und `create_all` ergänzt nie nachträglich Indizes auf existierenden Tabellen, d.h. ein Model-only-Index erreicht die laufende DB nie. Lesson aus einem anderen Projekt: fehlende Indizes auf FK-Spalten liefen dort 1,5 Jahre unbemerkt als Full-Table-Scan im Hot Path.

## Alembic-Migrationen

**Nie annehmen, dass die laufende DB dem Migrationsverlauf entspricht.** Manuelle Hotfixes, abgebrochene Läufe und divergierende Umgebungen (Dev/Prod) führen zu Drift — ein blindes `add_column`/`create_index` crasht dann die ganze Migration mittendrin. Jede Schema-Änderung kriegt einen Existenz-Check, damit die Migration re-run-sicher (idempotent) ist. Das Muster wird im Code bereits verwendet, hier nur nachdokumentiert:

```python
from alembic import op
import sqlalchemy as sa


def _has_table(table: str) -> bool:
    return sa.inspect(op.get_bind()).has_table(table)

def _has_column(table: str, column: str) -> bool:
    insp = sa.inspect(op.get_bind())
    return _has_table(table) and column in {c["name"] for c in insp.get_columns(table)}

def _has_index(table: str, index: str) -> bool:
    insp = sa.inspect(op.get_bind())
    return _has_table(table) and index in {ix["name"] for ix in insp.get_indexes(table)}
```

- Guards in **beide** Richtungen — `upgrade` *und* `downgrade`:
  ```python
  def upgrade() -> None:
      if not _has_column("users", "email"):
          op.add_column("users", sa.Column("email", sa.String(), nullable=True))
      if not _has_index("users", "ix_users_email"):
          op.create_index("ix_users_email", "users", ["email"])

  def downgrade() -> None:
      if _has_index("users", "ix_users_email"):
          op.drop_index("ix_users_email", table_name="users")
      if _has_column("users", "email"):
          op.drop_column("users", "email")
  ```
- **SQLite kann nicht wirklich `ALTER`** — Drop/Rename einer Spalte und die meisten Constraint-Änderungen scheitern direkt. In `op.batch_alter_table` wrappen (baut die Tabelle im Hintergrund neu); die Existenz-Checks bleiben *außerhalb* des Batch-Blocks.
- **Ehrlicher Tradeoff:** Ein Guard überspringt still, wenn das Objekt existiert, aber *falsch* ist (anderer Typ, Nullability, FK-Ziel). Er schützt vor "schon da", nicht vor "da, aber falsch". Bei Typ-/Constraint-Änderungen an einer möglicherweise gedrifteten Spalte die echte Definition prüfen, nicht nur den Namen.
- Eine logische Änderung pro Revision; eine bereits in eine andere Umgebung ausgerollte Migration nie nachträglich editieren — neue Revision anlegen.

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
