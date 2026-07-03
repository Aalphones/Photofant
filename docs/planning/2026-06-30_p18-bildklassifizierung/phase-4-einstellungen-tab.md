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

- [x] `models/classification.model.ts` (Kontrakt-Typen) + Barrel-Export (`@photofant/models`).
- [x] `services/classification.service.ts`: CRUD + `reclassifyAll()` (mappt auf `/classify/rerun`).
- [x] `store/classification/`: actions/reducer/selectors/effects (load + CRUD), in Root-Store registrieren.
- [x] `features/einstellungen/klassifizierung/` Shell + Child-Komponente(n) + scoped SCSS.
- [x] `einstellungen.types.ts` `SECTIONS` + `einstellungen.ts` Import/Template.
- [x] Tooltip-/Hilfe-Mikrotexte (Affordance) an den oben genannten Stellen.

## Report-Back

**Status:** complete.

- Shell `klassifizierung/klassifizierung.ts` lädt Kategorien, listet sie (inline rename per Doppelklick,
  Neuanlage, Löschen mit Bestätigung), wählt eine Kategorie aus und rendert den Child
  `kategorie-editor/kategorie-editor.ts` daneben (zweispaltiges Master-Detail-Layout, kein Mockup —
  freihändig nach Tags-Tab-Vorbild).
- `kategorie-editor` verwaltet Labels der ausgewählten Kategorie: anlegen/umbenennen/löschen,
  Modus-Umschalter single/multi, „Erweitert"-Aufklappung pro Label für eigene CLIP-Prompts /
  WD14-Tags (Grundfluss funktioniert ohne diese Felder — Prompt-Template greift automatisch).
- „Bestehende Bilder klassifizieren" dispatcht `reclassifyAll()` → `ClassifyService.rerun` (bestehende
  Rerun-Route, kein neuer Endpoint) — Fortschritt läuft automatisch ins bestehende Job-Dock, da dessen
  Polling jobunabhängig ist.
- Frontend-`ClassifyStep`-Union in `classify.service.ts` um `'categories'` ergänzt (Backend hatte es
  schon in Phase 3; im Frontend fehlte es noch).
- Alle Erklärungs-Affordances als `title`-Tooltip umgesetzt (Tastaturkürzel-Tab-Konvention) — kein
  dediziertes Tooltip-Component im Projekt vorhanden, daher kein neues eingeführt.
- `npm run lint` (tsc --noEmit) + `npm run build` grün.
