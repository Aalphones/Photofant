# Linting Conventions — Photofant

> **Builds on user-level baseline.** Project overrides below take precedence.

## Stack

| Layer | Choice |
|---|---|
| Python | `ruff` (Lint + Format) + `mypy --strict` |
| TypeScript/Angular | `angular-eslint` + `prettier` |

## Python (`ruff`)

- Regelsatz: `E, W, F, I, UP, B, C4, SIM` (pyflakes, pycodestyle, isort, pyupgrade, bugbear, comprehensions, simplify)
- Zeilenlänge: 120
- `mypy --strict` für neuen Code
- `# noqa: F401` ist absichtlich bei load-bearing Imports (Registry-Side-Effects, Forward-Refs) — nicht entfernen, ohne zu prüfen; type-only Imports bevorzugt in `if TYPE_CHECKING:`

## TypeScript/Angular

- `angular-eslint` mit empfohlenem Regelsatz, Template-Linting aktiv
- `prettier` mit Defaults; keine Stil-Diskussionen im Review — die Tools entscheiden
- Konfiguration wird in Stage 0 angelegt und gepinnt

## Critical Rules

1. **Lint-Fehler werden gefixt, nicht per Inline-Disable weggedrückt** — Ausnahmen brauchen einen Kommentar mit Grund.
2. **`ci.cmd` muss vor jedem Code-Commit grün sein.**
