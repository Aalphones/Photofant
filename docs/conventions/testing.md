# Testing Conventions — Photofant

> **Builds on user-level baseline.** Project overrides below take precedence.

## Stack

| Layer | Choice |
|---|---|
| Backend | `pytest` |
| Frontend | Angular-Test-Runner (bei Stage 0 pinnen: Vitest-basiert, falls vom CLI-Major unterstützt) |

## Backend (`pytest`)

- Fixtures statt setUp/tearDown
- `@pytest.mark.parametrize` für repetitive Fälle
- Tests in `backend/tests/`, Struktur spiegelt das Package
- DB-Tests gegen eine Wegwerf-SQLite (tmp_path), nie gegen echte Daten

## Frontend

- Komponenten-Tests für Logik (Signals, Stores, Pipes); kein Pixel-Snapshot-Theater
- NgRx: Reducer und Selectors als reine Funktionen testen, Effects mit Marble- oder Promise-Pattern

## Grundsätze

- **Features mit Unit-Tests absichern** — neue Logik kommt mit Tests im selben Commit/Phase.
- **Nach Code-Änderungen die zugehörigen Tests laufen lassen**, Failures sofort fixen.
- Schwere ML-Inferenz wird nicht in Unit-Tests gezogen — Inferenz-Layer hinter Interfaces mocken; echte Modell-Läufe sind manuelle Smoke-Tests.

## Critical Rules

1. **Kein Merge/Commit von rotem Stand** — `ci.cmd` grün ist die Grundbedingung.
2. **Idempotenz der Pipeline ist testpflichtig** — der Once-Only-Mechanismus (`processing_ledger`, Content-Hash) bekommt explizite Tests, da Datenverlust-kritisch.
3. **Move-Operationen (Favoriten, Korrekturen) testpflichtig** — physischer Move + DB-Pfad-Update müssen atomar zusammenpassen.
