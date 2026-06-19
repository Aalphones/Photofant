# ADR-004 — Einstellungen: Master-Detail-Shell statt Einspalten-Scroll

**Status:** Accepted  
**Datum:** 2026-06-19  
**Kontext:** Design-Angleichung Phase 2

## Kontext

Die Einstellungen-Seite bestand aus einem flachen Einspalten-Scroll (`settings-layout`, `max-width: 680px`) mit selbst erfundenen `settings-card`/`card-row`-Klassen. Das Mockup (`docs/design/js/settings.jsx`) sieht ein zweispaltiges macOS-Settings-Muster vor: linke Sektions-Nav mit Icons + rechter Inhaltsbereich (ein Abschnitt sichtbar).

## Optionen

1. **Master-Detail in `einstellungen.ts`** — Shell als CSS-Klassen im Component-Styles-Block, `@switch`/`@case` für die Sektionen, Signal für aktive Sektion. Kein neues Subdir.
2. **Separate Subcomponents** — je Sektion eine eigene Standalone-Component in `features/einstellungen/components/`. Sauberer, aber Overhead für 7 überschaubare Sektionen ohne eigene Store-Selectors.
3. **Router-Outlet** — Child-Routes pro Sektion (`/einstellungen/bibliothek`). Unnötig: keine tiefen URLs nötig, Sektionswechsel ist UI-State, kein App-State.

## Entscheidung

Option 1. Die gesamte Shell liegt in `einstellungen.ts` als `@switch`-Block; CSS-Primitive (`st-page`, `st-nav`, `st-group`, `st-row`, `st-switch`, `st-note`, `st-btn`, `st-path`) sind im Component-`styles`-Block definiert, scoped per Angular View Encapsulation. Keine Router-Änderung.

## Konsequenzen

- **Positiv:** Kein neues Routing, keine separaten Dateien, CSS-Budget bleibt unter 8 kB (angular.json `anyComponentStyle: maximumError`), Mobile-Support via einfaches Signal + CSS-Toggle.
- **Negativ:** Alle Sektionen in einer Datei — wird unhandlich wenn >10 Sektionen oder Sektionen eigene komplexe Stores brauchen. Dann Option 2 nachziehen.
- **Offen:** Tastaturkürzel-Sektion listet heute nur Lightbox-Shortcuts. Weitere Gruppen können per `SHORTCUT_ROWS`-Erweiterung ergänzt werden, ohne Shell-Umbau.
