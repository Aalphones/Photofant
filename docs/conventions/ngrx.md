# NgRx Conventions — Photofant

> **Stack** (pinned for this project):
> | Layer | Choice |
> |---|---|
> | State | NgRx classic: `@ngrx/store` + `@ngrx/effects` + `@ngrx/entity` + `@ngrx/operators` |
>
> **Builds on user-level baseline.** Project overrides below take precedence. Die Feature-Slices des Projekts definiert das Konzept, Sektion 15.

## Folder Layout pro Feature

```
store/
├── <feature>/
│   ├── <feature>.actions.ts
│   ├── <feature>.reducer.ts
│   ├── <feature>.effects.ts
│   ├── <feature>.selectors.ts
│   └── index.ts                # Barrel — re-exportiert die Public Surface
├── global.actions.ts           # cross-cutting (Bootstrap etc.)
└── index.ts                    # re-exportiert jedes Feature-Barrel
```

Jedes neue Feature wird im Root-Barrel ergänzt — fehlende Einträge erzwingen Deep-Imports, die sich fortpflanzen.

## Actions: `createActionGroup`

- **Eine `createActionGroup` pro Feature** — keine losen `createAction`-Aufrufe
- `source` = Feature-Name in Title Case; Event-Namen mit Leerzeichen (`'Add Annotation'` → `addAnnotation`)
- Imperativ für Commands (`Create`, `Send`), `… Success`/`… Failure` für Outcomes
- `;` als Separator in `props<{ … }>()`
- Failure-Props enthalten immer den typisierten Fehler (`error: HttpErrorResponse`)

## Reducer

- **State-Parameter explizit typen** in jedem `on()`-Handler
- **Kein `state.foo!`** — früh guarden (`if (!id) return state;`) oder `?.`
- **`createEntityAdapter`** für jede ID-keyed Collection (assets, persons, tags, …) — kein Eigenbau
- **Reducer ist pur** — kein `new Date()`, kein I/O, kein `Math.random()`; Timestamps/UUIDs entstehen in Effects oder im Payload
- Initial-State als benannte Konstante

## Selectors: `createFeature` + Komposition

- **`createFeature` ist der Einstieg** — auto-generierte Selectors nicht von Hand schreiben
- Composite-Selectors via `createSelector`, Projector-Args explizit typen
- **Ein `<feature>Selectors`-Objekt exportieren**, das `createFeature`-Output spreaded und Composites ergänzt
- Keine Side-Effects in Selectors (bricht Memoization)

## Effects

- `private readonly actions$ = inject(Actions);` — `actions$` ist das einzige legitime `$`-Feld in einer Effects-Klasse
- Felder heißen `on<Action>$` für non-dispatching Effects (`{ dispatch: false }`), Verb-Namen für dispatchende
- **`switchMap`** als Default (latest-wins), `concatMap` wenn Reihenfolge zählt, `mergeMap` für echte Parallelität
- **`concatLatestFrom` statt `withLatestFrom`**; kein `!` auf den Werten — `if (!x) return EMPTY;`
- **Kein `delay(N)`**, um auf den Reducer zu warten — `concatLatestFrom` liest Post-Reducer-State
- `catchError`-Fehler typen: `(error: HttpErrorResponse) => …`
- HTTP-Responses über das Generic typen (`.get<Asset[]>()`), nie `Observable<any>`
- Kein `.subscribe()` im Effect — Observable zurückgeben, NgRx subscribed

## In Komponenten

- **`store.selectSignal(selector)`** statt `store.select() | async`
- Dispatch aus Event-Handlern, nicht aus `ngOnInit`-Side-Effects; „load on view" über Resolver oder guarded `effect()`
- `store` heißt `store`, nicht `$store`

## Projekt-Spezifika

- **`jobs`-Slice:** wird von SSE-Effects (`/jobs/stream`) live aktualisiert — alle Fortschrittsanzeigen (Import, Klassifizierung, Downloads) hängen daran
- **`editor`-Slice:** temporäre In-Memory-Step-Historie; persistiert wird nur beim bewussten Speichern (API `save-version`)
- **Optimistische Updates** (Favorit, Tag-Edit) sind erwünscht — Rollback-Action im Failure-Fall

## Anti-Patterns (Review-Blocker)

- ❌ `state.foo!` im Reducer · ❌ `Observable<any>` · ❌ untypisierte Reducer-Lambdas
- ❌ `delay()` als Reducer-Synchronisation · ❌ `database$ = inject(DatabaseService)` (Service ≠ Observable)
- ❌ leerer `constructor() {}` · ❌ Feature fehlt im Root-Barrel
- ❌ Selectors mit Side-Effects · ❌ Classic Store und Signal Store für dieselbe Slice

## Critical Rules

1. **Pure Reducer, typisierte Handler, EntityAdapter für Collections** — keine Ausnahmen.
2. **Ein Feature = ein Slice-Ordner mit festem Datei-Set + Barrel-Eintrag.**
3. **Kein NgRx für rein lokalen UI-State** — Modal-/Form-Transienten bleiben Signals.
