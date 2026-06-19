# Einstellungen-Refactoring — Monolith → Clean Components

> Status: pending · Eigentümer: Frontend · Setzt an NACH `2026-06-19_design-angleichung` (Shell ist dann stabil)

`einstellungen.ts` wurde als 970-Zeilen-Monolith gebaut: Inline-Template, Inline-Styles, alle 7 Sektionen im `@switch` der Shell, Interface-Deklarationen inline, CSS-Klassen mit kryptischen Präfixen (`st-`, `sp-`, `sc-`). Dieser Plan zerlegt die Datei nach den geltenden Angular-Regeln.

## Overview

| # | Phase | Rating | Status |
|---|---|---|---|
| 1 | [Shell-Trennung: HTML/SCSS/Types auslagern](phase-1-shell-trennung.md) | mechanisch | complete |
| 2 | [Child-Komponenten via ng generate](phase-2-child-komponenten.md) | standard | complete |
| 3 | [BEM-Bereinigung + Parent aufräumen](phase-3-bem-bereinigung.md) | mechanisch | complete |

## Kontrakt

Rein **Frontend**. Keine API-Änderungen. Alle bestehenden Store-Selektoren und -Actions bleiben unverändert — sie wandern nur von der Shell in die jeweiligen Child-Komponenten.

## Architektur-Entscheidungen

Keine offenen ADRs — alle Entscheidungen sind durch bestehende Angular-Konventionen gedeckt:
- Child-Komponenten per `ng generate` (keine manuellen Dateien)
- Child-Komponenten greifen direkt via `inject(Store)` auf den Store zu — kein Input-Passing vom Parent
- Load-Actions werden von der jeweiligen Child-Komponente dispatcht (lazy, beim ersten Rendern) statt alle auf einmal in der Shell

## Finale Akzeptanzkriterien

1. `einstellungen.ts` enthält ausschließlich Navigationslogik: `activeSection`, `mobileOpen`, `sections`, `goSection()`, `goBack()` — alle sektionsspezifischen Signals, Methoden und Store-Selektoren sind entfernt.
2. Jede der 7 Sektionen ist eine eigenständige Child-Komponente mit `.ts` + `.html` + `.scss`, angelegt via `ng generate`.
3. `einstellungen.types.ts` enthält `Section` und `ShortcutRow`; die Shell-Klasse hat keine Interface-Deklarationen mehr.
4. Alle CSS-Klassen in Templates folgen BEM mit vollem Block-Namen nach Selektor (kein `st-`, `sp-`, `sc-`-, `.on`-Modifier ohne Block); kein Inline-Style im Template.
5. Alle bestehenden Funktionen (Backup, Modell-Ordner, Caption-Presets, Darstellung, Shortcuts, Info) sind funktionsfähig.

## Smoke-Checkliste (User, am Plan-Ende)

- [ ] Einstellungen öffnen → alle 7 Sektionen per Klick navigierbar, kein sichtbarer Unterschied zum vorherigen Stand.
- [ ] Backup erstellen → läuft durch, Backup erscheint in der Liste.
- [ ] Sammlungs-Ordner ändern → Reboot-Banner erscheint.
- [ ] Caption-Preset anlegen → Dialog öffnet sich, Preset wird gespeichert.
- [ ] Darstellung-Toggle umlegen → Einstellung bleibt nach Page-Reload erhalten.
- [ ] Shortcut ändern → neue Taste wird gespeichert und beim nächsten Öffnen angezeigt.
- [ ] Mobile-View (< 860px) → Navigation klappt ein/aus per Zurück-Button.
- [ ] `einstellungen.ts` öffnen → kein `template:`, kein `styles:`, kein inline Interface (`ShortcutRow`, `Section`).

## Summary

Monolith `einstellungen.ts` (970 Zeilen, Inline-Template, Inline-Styles) in eine saubere Shell + 8 eigenständige Child-Komponenten zerlegt. Alle CSS-Klassen von kryptischen Präfixen (`st-`, `sp-`, `sc-`) auf vollständige BEM-Namen umgestellt. Plan komplett in 3 Phasen abgeschlossen.

## Files touched

- `frontend/src/app/features/einstellungen/` — Shell + alle 8 Child-Komponenten
- `frontend/src/app/features/einstellungen/_st-shared.scss` — auf Utilities getrimmt
- `frontend/src/app/features/einstellungen/einstellungen.types.ts` — neu (Phase 1)

## Commits

- Phase 1: `refactor(einstellungen): phase 1 — extract template, styles and types into separate files`
- Phase 2: `refactor(einstellungen): phase 2 — split monolith into 8 child components`
- Phase 3: `refactor(einstellungen): phase 3 — BEM-Bereinigung aller st-/sp-/sc-Klassen`

## Deviations from plan

- `tags`-Komponente war nicht im ursprünglichen 7-Komponenten-Plan: SECTIONS hat 8 Einträge. In Phase 2 hinzugefügt, BEM in Phase 3 eingebaut.
- `_st-shared.scss` gelöscht nicht leer gemacht: Datei bleibt als Import-Ankerpunkt für Utilities (`code`, `.spinner`, `.group-loading`, `.group-empty`, `.error-banner`).

## Follow-ups

- Budget-Warning `tags.scss` (5.6 KB > 4 KB Budget): Dialog-Styles könnten in eigene Komponente extrahiert werden — kein Blocker.
