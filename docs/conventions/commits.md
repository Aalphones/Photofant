# Commit Conventions — Photofant

> **Builds on user-level baseline.** Project overrides below take precedence.

## Format

**Conventional Commits**, Message erklärt das **Why**, nicht das What (das zeigt der Diff):

```
<type>(<scope>): <kurze Zusammenfassung>

<optional: Begründung / Kontext>
```

- **Types:** `feat`, `fix`, `refactor`, `chore`, `docs`, `test`, `perf`
- **Scopes:** `backend` | `frontend` | `docs` | `design` | `setup` — weglassen, wenn der Commit das ganze Repo betrifft

## Regeln

- **Tidy First — Refactor ≠ Verhalten:** Refactoring und Verhaltensänderung nie im selben Commit. Refactor-Commit = Tests unverändert grün; Feature/Fix-Commit = neue/geänderte Tests.
- **Keine Attribution-Footer** — keine generierten `Co-Authored-By`- oder Tool-Werbe-Zeilen in Messages.
- **Vor dem Commit:** `ci.cmd` laufen lassen, wenn Code geändert wurde.

## Critical Rules

1. **Niemals Secrets committen** — bei `.env`, `credentials*`, `*token*`, `*.pem` im Diff: stoppen und prüfen.
2. **Keine Modell-Binaries committen** — auch nicht „nur kurz zum Testen".
3. **Force-Push, `--amend` auf Gepushtes, `git reset --hard` nur nach expliziter Rückfrage.**
