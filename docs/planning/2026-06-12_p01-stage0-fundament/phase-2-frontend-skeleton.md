# P1 · Phase 2 — Frontend-Skeleton

> Rating: standard · Status: complete

## Kontext (vorher lesen)

- [README.md](README.md) — Kontrakt (SSE-Schema, Proxy)
- [docs/design/README.md](../../design/README.md) — App-Shell-Sektion, Design-Tokens, Responsive Breakpoints
- `docs/design/styles.css` (Token-Quelle), `docs/design/js/app.jsx` (Shell-Verhalten als Referenz)
- [docs/conventions/angular.md](../../conventions/angular.md), [ngrx.md](../../conventions/ngrx.md)

## Akzeptanzkriterien

- Angular-Workspace unter `frontend/` mit Prefix `pf`, strict TS (Flags aus typescript.md), Path-Aliases + Barrels.
- Tailwind v4 eingebunden; **alle** Tokens aus `docs/design/styles.css` (Farben, Radien, Schatten, Layout-Maße, Fonts) als `@theme`-Custom-Properties.
- App-Shell pixel-orientiert am Prototyp: Nav-Rail (212 px, Brand, Gruppen, Count-Badges), Top-Bar (58 px), Responsive-Verhalten ≤860 px (Drawer + Bottom-Tab-Bar).
- Routing-Gerüst: lazy Platzhalter-Routen für galerie/personen/alben/trainingssets/modelle/einstellungen.
- `jobs`-NgRx-Slice wird über SSE-Effects gespeist; Job-Pill + Job-Dock (Popover/Bottom-Sheet) zeigen den Demo-Job live.

## Checkliste

- [x] Workspace generieren (`ng new`), Prefix `pf`, SCSS, strict; tsconfig-Flags + Aliases `@photofant/*` mit Barrels
- [x] Tailwind v4 + `@theme`-Block aus `docs/design/styles.css` übertragen; IBM Plex Mono einbinden (lokal, kein CDN — Offline-Prinzip)
- [x] App-Shell-Komponenten: `shell`, `nav-rail`, `top-bar` (BEM + scoped SCSS, `:host`-Regeln beachten)
- [x] Routen-Gerüst mit `loadComponent`-Platzhaltern
- [x] NgRx-Grundverdrahtung (`provideStore`, `provideEffects`), `store/jobs/`-Slice nach ngrx.md inkl. SSE-Effect (EventSource → Actions)
- [x] Job-Pill (Spinner-Zustand) + Job-Dock (Desktop-Popover, Mobile-Sheet) gegen den Demo-Job
- [x] Dev-Proxy `/api` → Backend-Port
- [x] Doc-Update: AGENTS.md Stack-Tabelle (Angular-Major, Test-Runner pinnen)

## Report-Back
