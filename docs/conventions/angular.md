# Angular Conventions — Photofant

> **Source-of-truth references:**
> - [angular.dev Best Practices](https://angular.dev/assets/context/best-practices.md) (optional als Snapshot nach `.claude/angular-<version>-best-practices.md` vendoren)
> - `docs/design/` — High-Fidelity-Prototypen; `docs/design/styles.css` ist die kanonische Token-Quelle
>
> **Stack** (pinned for this project):
> | Layer | Choice |
> |---|---|
> | Framework | Angular, aktuelles Major (bei Stage 0 exakt pinnen) |
> | Styling | Tailwind v4 als Token-Quelle (`@theme`), BEM + scoped SCSS |
> | State | NgRx classic ([ngrx.md](ngrx.md)) für Server-State, Signals lokal |
> | Tests | Angular-Test-Runner, Pin bei Stage 0 |
>
> **Builds on user-level baseline.** Project overrides below take precedence. TypeScript-Grundregeln: [typescript.md](typescript.md).

## Library Policy

**Forbidden:**
- Angular Material / fertige UI-Kits — das Design-System kommt vollständig aus den Prototypen (`docs/design/`)
- `ngModel` / Template-driven Forms

**Allowed:**
- `@ngrx/store`, `@ngrx/effects`, `@ngrx/entity`, `@ngrx/operators` — Server-State (siehe [ngrx.md](ngrx.md))
- `@angular/cdk` — nur einzelne Primitives (Overlay, A11y), falls nötig

## Project Layout

```
frontend/src/app/
├── features/<feature>/        # Views: gallery, persons, albums, models, settings, editor, …
│   └── <subcomponent>/        # nur dort genutzte Kinder bleiben genested
├── store/<feature>/           # NgRx-Slices (siehe ngrx.md)
├── ui/                        # cross-feature Primitives (Buttons, Chips, Dialoge)
├── services/                  # ein Service pro Backend-Ressource
└── models/                    # Interfaces/Types zur API
```

Path-Aliases in `tsconfig.json`: `@photofant/models`, `@photofant/services`, `@photofant/store`, `@photofant/ui` — je mit Barrel-`index.ts`, das bei jedem Feature mitgepflegt wird.

## Naming & Generierung

- Selector-Prefix: **`pf`** (`pf-gallery`, `pf-person-card`) — in `angular.json` setzen
- Moderner Style-Guide: Komponenten/Direktiven ohne Suffix (`gallery.ts` / Klasse `Gallery`); Services/Pipes/Guards behalten ihren Suffix (`asset.service.ts`)
- **Nie Dateien von Hand anlegen** — immer `ng generate`, ohne `--inline-template`/`--inline-style`; jede Komponente bekommt `.ts` + `.html` + `.scss`

## Components

- **`ChangeDetectionStrategy.OnPush` auf jeder Komponente** — auch Page-Level
- **Signals statt Decorators:** `input.required<T>()`/`input<T>()`, `output<T>()`, `model<T>()`, `viewChild()`/`viewChildren()`, `contentChild()`/`contentChildren()`; alle als `readonly`
- State-Updates über `signal.set()`/`signal.update((prev: T) => …)` — nie mutieren; Update-Callbacks explizit typen
- Host-Bindings im `host`-Objekt, nicht `@HostBinding`/`@HostListener`
- Kein leerer `constructor() {}`; `inject()` per Field-Init
- Kein `!` auf injizierten/gequerten Feldern — nullable typen und behandeln

## `:host` ist der erste Container — kein Wrapper-Div

- Die Komponente selbst ist das Root-Element: `:host` stylen, keinen `<div class="root">` drumwickeln
- `:host` deklariert **immer** ein `display` (Custom Elements sind sonst `inline`)
- Wrapper-Heuristik: Root-`<div>` mit Geschwister-Inhalten → behalten; nur ein Kind oder reine Layout-Klassen → killen, Klassen auf `host`; `#ref` für Observer → Host via `inject(ElementRef)` beobachten
- `<ng-container>` wenn eine Direktive, aber kein DOM-Element gebraucht wird

## Templates

- `@if`, `@for` (mit `track`), `@switch` — nie `*ngIf`/`*ngFor`/`*ngSwitch`
- **BEM-Klassennamen, keine Utility-Klassen** im Template — `gallery__cell--selected`; Conditional Classes via `[class.…]`-Binding, nie `ngClass`/`ngStyle`
- Async Pipe bzw. `selectSignal` — keine Business-Logik im Template

## Styling — Tokens aus den Prototypen

- **Tailwind v4 dient ausschließlich als Token-Quelle** (`@theme`): die Custom Properties aus `docs/design/styles.css` (`--bg`, `--surface`, `--accent`, `--radius`, …) werden dort definiert. **Keine Utility-Klassen in Templates.**
- Visuelles Styling lebt in komponenten-scoped SCSS, verdrahtet über `var(--token)` — keine hartcodierten `px`/`hex` in Komponenten-SCSS
- Animationen per `@keyframes` im SCSS; `prefers-reduced-motion` respektieren (Prototyp macht's vor)

## Services & DI

- **`inject()`-Funktion, nie Constructor-Injection** — überall
- Ein Service pro Backend-Ressource, `providedIn: 'root'` für Singletons
- **Kein `.subscribe()` in Komponenten** — `toSignal()` oder Async Pipe; einmalige Side-Effects mit `takeUntilDestroyed(this.destroyRef)`
- `DOCUMENT`/`PLATFORM_ID` injizieren statt Globals anfassen; `localStorage`-Zugriff in einen dünnen Service wrappen

## Forms

- **Nur Reactive Forms**; `FormBuilder` via `inject()`, `nonNullable.control()` für Pflichtfelder
- Controls über das typisierte `controls.foo`, nie `controls['foo']`
- Abgeleiteter Form-State: `toSignal(form.valueChanges)` + `computed()` statt `combineLatest().subscribe()`

## Routing

- **Lazy via `loadComponent`/`loadChildren`** für jede Feature-Route; eager nur die Shell
- Funktionale Guards (`CanActivateFn`), Interceptors (`HttpInterceptorFn`), Resolvers (`ResolveFn`) — keine Klassen

## State Management

- **Lokaler UI-State:** Signals + `computed()` + `effect()`
- **Server-State über Routen hinweg:** NgRx classic nach [ngrx.md](ngrx.md) — die Feature-Slices stehen im Konzept (Sektion 15): gallery, filters, search, selection, persons, editor, tags, collections, promptTemplates, trash, maintenance, jobs, settings
- Nie beide Welten für dieselben Daten; Konsum in Komponenten via `store.selectSignal(...)`
- Der Editor hat einen eigenen Slice mit temporärer In-Memory-Step-Historie (wird beim Speichern verworfen)

## Images

- `NgOptimizedImage` für statische Bilder; Galerie-Thumbnails laden lazy mit Gradient-Platzhalter (siehe `docs/design/README.md`, `Img`-Primitive)

## Critical Rules

1. **`OnPush` überall** — die Galerie lebt von Rendering-Performance.
2. **Keine Utility-Klassen in Templates** — BEM + Token-SCSS; Tailwind ist nur Token-Lieferant.
3. **Signals-API statt Decorator-API** — `@Input()`/`@Output()`/`EventEmitter` sind Review-Blocker.
4. **Kein `.subscribe()` in Komponenten ohne `takeUntilDestroyed`.**
5. **Pixel-Treue zu `docs/design/`** — Tokens, Spacing und Verhalten kommen aus den Prototypen, nicht aus dem Bauch.
