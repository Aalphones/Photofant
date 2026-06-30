# Phase 4 — Einstellungen-Tab (Frontend)

**Tier:** standard (kein neues Design — freihändig nach Bestand, Tags-Tab als Vorbild)

## Kontext (vor Start lesen)

- [`frontend/src/app/features/einstellungen/einstellungen.ts`](../../../frontend/src/app/features/einstellungen/einstellungen.ts) + [`einstellungen.types.ts`](../../../frontend/src/app/features/einstellungen/einstellungen.types.ts) — Shell, `SECTIONS`-Liste, Master-Detail (ADR-004).
- [`frontend/src/app/features/einstellungen/tags/tags.ts`](../../../frontend/src/app/features/einstellungen/tags/tags.ts) — **strukturelles Vorbild**: Liste, Inline-Rename, Store-Anbindung, Signals.
- [`docs/conventions/angular.md`](../../../docs/conventions/angular.md) + [`ngrx.md`](../../../docs/conventions/ngrx.md).
- [`docs/design/README.md`](../../../docs/design/README.md) Abschnitt „8. Einstellungen" — generische Bausteine (`Group`, `Row`, `SliderRow`), an denen sich der Look orientiert.

> **Design-Hinweis:** Für diesen Tab existiert **kein Mockup** (von Sascha bestätigt: freihändig nach Bestand). Look = vorhandene Settings-Bausteine + Tags-Tab-Struktur. Keine pixelgenaue Kontrakt-Bindung, aber AK unten nageln die Struktur fest.
>
> **Komponenten-Aufspaltung (Projekt-Regel):** Shell + Child-Komponenten, **kein Monolith**, kein Inline-Template, kein kryptisches CSS.

## Akzeptanzkriterien

1. Neuer Eintrag in `SECTIONS` (`id: 'klassifizierung'`, passendes Icon aus der
   vorhandenen Icon-Registry, Label „Klassifizierung"); in `einstellungen.ts`
   eingebunden.
2. Tab ist als **Shell + Child** gebaut:
   - Shell `klassifizierung/` lädt Kategorien aus dem Store, listet sie.
   - Child „Kategorie-Editor": Labels einer Kategorie anlegen/umbenennen/löschen,
     Modus-Umschalter (single/multi).
   (Konkreter Schnitt liegt beim Umsetzer, aber **mindestens** diese zwei Ebenen.)
3. CRUD vollständig über UI bedienbar: Kategorie anlegen/umbenennen/löschen,
   Label anlegen/umbenennen/löschen, Modus wechseln — alles über `store/classification`.
4. Button „Bestehende Bilder klassifizieren" stößt den Retro-Lauf an
   (`POST /classify/rerun {asset_ids:"all", steps:["categories"]}`); Fortschritt
   landet im bestehenden Job-Dock.
5. **Erklärungs-Affordance (Idiotensicherheits-Gate):** Jede nicht-triviale
   Stelle hat eine dezente, optionale Erklärung (i-/?-Icon oder Tooltip):
   - Modus single vs. multi („eine Hauptklasse" vs. „mehrere möglich").
   - „Bestehende Bilder klassifizieren" (läuft im Hintergrund über alle Bilder,
     kann dauern).
   - Erweiterte Felder (eigene CLIP-Prompts, WD14-Tag-Zuordnung) hinter einer
     „Erweitert"-Aufklappung pro Label — Grundfluss (Kategorie benennen, Labels
     tippen) funktioniert **ohne** sie, weil das Prompt-Template greift.
6. `store/classification`, `services/classification.service.ts`,
   `models/classification.model.ts` nach Kontrakt-Typen angelegt.
7. `npm run lint` + `npm run build` grün. (Private-Profil: kein `ng test`.)

## Checkliste

- [ ] `models/classification.model.ts` (Kontrakt-Typen) + Barrel-Export (`@photofant/models`).
- [ ] `services/classification.service.ts`: CRUD + `reclassifyAll()` (mappt auf `/classify/rerun`).
- [ ] `store/classification/`: actions/reducer/selectors/effects (load + CRUD), in Root-Store registrieren.
- [ ] `features/einstellungen/klassifizierung/` Shell + Child-Komponente(n) + scoped SCSS.
- [ ] `einstellungen.types.ts` `SECTIONS` + `einstellungen.ts` Import/Template.
- [ ] Tooltip-/Hilfe-Mikrotexte (Affordance) an den oben genannten Stellen.

## Report-Back
