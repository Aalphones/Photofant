# TypeScript Conventions — Photofant

> **Stack** (pinned for this project):
> | Layer | Choice |
> |---|---|
> | TypeScript | strict, Version folgt Angular-CLI |
>
> **Builds on user-level baseline.** Project overrides below take precedence. Angular-spezifische Regeln: [angular.md](angular.md).

## Strict Mode (tsconfig)

- `strict: true` — nicht verhandelbar
- `noUncheckedIndexedAccess: true` — Array-/Objekt-Zugriff liefert `T | undefined`
- `noUnusedLocals: true`, `noUnusedParameters: true`
- `exactOptionalPropertyTypes: true`
- `noImplicitOverride: true`

## Types

- Funktionsparameter und Returns: immer explizit; Inference nur für offensichtliche lokale Variablen
- `unknown` statt `any`; mit Type Guards narrowen
- Nie `as any` — wenn Escape nötig: `as unknown as T` plus Begründungskommentar

## Discriminated Unions statt Magic Strings

```ts
type AssetSource = 'original' | 'sdxl' | 'flux';

// Mit unterschiedlichen Payloads:
type ModelStatus =
  | { kind: 'active' }
  | { kind: 'available'; sizeBytes: number }
  | { kind: 'missing'; reason: string };
```

## Enums

Const-asserted Unions statt `enum`:

```ts
export const FRAMINGS = ['close_up', 'medium', 'full_body'] as const;
export type Framing = typeof FRAMINGS[number];
```

## Nullability

- `undefined` für „noch unbekannt", `null` für „explizit abwesend" — die API liefert `null`, im Frontend gilt daher **`null` als Default** für Abwesenheit
- **Kein `!` Non-Null-Assertion** — Type Guard oder Refactoring

## Imports & Modules

- `import type` für Type-only-Imports
- Absolute Imports über Path-Aliases (`@photofant/...`), nie `../../../`
- Barrel-Files nur für die in [angular.md](angular.md) definierten Alias-Ordner

## Functions

- Kein `Function`-Typ — konkrete Signatur
- `Readonly<T>` / `readonly`-Arrays für Parameter, die nicht mutieren dürfen
- Async: explizites `Promise<T>`-Return
- Lambda-Parameter explizit typen (`filter`, `map`, RxJS-Operatoren, `signal.update`)

## Naming

- PascalCase: Typen, Interfaces, Klassen, Komponenten
- camelCase: Funktionen, Variablen, Methoden
- SCREAMING_SNAKE_CASE: echte Konstanten
- `$`-Suffix nur für Felder, deren Wert ein Observable IST

## Critical Rules

1. **`strict: true` bleibt an** — kein Lockern einzelner Flags, um einen Build zu retten.
2. **Kein `any`, kein `!`** — beide sind Review-Blocker.
3. **Caught Errors als `unknown`** typen und narrowen.
