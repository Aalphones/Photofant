# Phase 2 — Einstellungen-Shell + Primitive

> Rating: heikel · Status: complete (2026-06-19)

Ersetzt die flache Einspalten-Hülle der Einstellungen durch das Master-Detail-Layout des Mockups und zieht **alle** Sektionen in wiederverwendbare Primitive um. Architektur-Entscheidung → **ADR-004**.

## Kontext (vorher lesen)

- [README.md](README.md) — Kontrakt, finale AK
- [docs/design/README.md](../../design/README.md) — Abschnitt „Einstellungen" (6 Sektionen, Komponenten Switch/Row/Group/SliderRow/PathRow)
- `docs/design/js/settings.jsx` — **Soll-Struktur**: `st-page` (links `st-nav` Sektions-Liste, rechts `st-body` eine aktive Sektion, Mobile-Drawer); Primitive `Switch`/`Row`/`Group`/`Note`/`PathRow`/`SliderRow`/`OpButton`; Sektions-Kopf `st-section-head` (`<h2>` + `<p>`)
- `docs/design/settings.css` — exakte Maße/Tokens der Primitive
- `frontend/src/app/features/einstellungen/einstellungen.ts` — **Ist-Zustand** (flache `settings-layout`, `max-width:680`, eigene `settings-card`/`card-row`; bereits korrekt: `st-switch`, `st-select`)
- [docs/conventions/angular.md](../../conventions/angular.md) — Standalone-Components, OnPush, Signals

## Chesterton's Fence — verstanden

Die heutige `einstellungen.ts` ist **funktional korrekt verdrahtet**: Signals + Store-Dispatches für Darstellung (SettingsService), Modell-Ordner (modelsActions), Backup (maintenanceActions), Caption-Presets (presetsActions), inkl. `effect()`-Initialload und Preset-Dialog. Diese Verdrahtung muss **vollständig erhalten** bleiben — diese Phase strukturiert nur das **Template + die Hülle** um, nicht die Logik. Kein Store-Verhalten, keine Service-Calls entfernen.

## Akzeptanzkriterien

- **Hülle nach Mockup**: zweispaltiges `st-page` — links Sektions-Nav (Liste mit Icon + Label, aktive Markierung), rechts genau **eine** aktive Sektion; Sektionswechsel ohne Reload; Mobile (≤860px): Nav als Drawer, Zurück-Pfeil im Body (wie `settings.jsx` `section-open`/`section-closed`).
- **Sektions-Kopf**: jede Sektion mit großem `<h2>`-Titel + erklärendem Untertitel (`st-section-head`), nicht dem heutigen 13px-Uppercase-Mini-Label.
- **Wiederverwendbare Primitive** (als kleine Standalone-Components oder Template-Partials + SCSS nach `settings.css`): `Row` (Title/Sub/Ctrl), `Group` (gruppierte Liste + Label), `Switch` (vorhanden, übernehmen), `SliderRow`, `PathRow`, `Note`, `OpButton`, Select (vorhanden). Künftige Sektionen lassen sich damit deklarativ zusammensetzen.
- **Sektions-Taxonomie nach Mockup**: die vorhandenen Inhalte werden den Design-Sektionen zugeordnet — Darstellung; Bibliothek (Modell-Ordner-Picker zieht hierher, wie im Mockup); Backup & Wartung (Backup zieht hierher); Verarbeitung/Tastaturkürzel/Info (aus `einstellungen-fehlende-sektionen`); Bearbeitung/Caption-Presets als eigene Sektion. Keine Ad-hoc-Sektionen „Modelle"/„Backup" mehr als Top-Level-Erfindung.
- **Funktionserhalt**: Backup-Trigger + Liste, Modell-Ordner-Edit, Caption-Preset-CRUD, Darstellung-Toggles, Sprache/Datumsformat — alle wie vor dem Refactor.
- **ADR-004** in `docs/decisions/004-*.md` angelegt (Kontext/Optionen/Entscheidung/Konsequenzen).

## Checkliste

- [x] Primitive anlegen — als CSS-Klassen in Component-Styles nach `settings.css`-Maßen (kein separates Components-Subdir, da alle in `einstellungen.ts` scoped)
- [x] `st-page`-Shell mit Sektions-Nav + aktivem-Sektion-Signal + Mobile-Drawer (`section-open`/`section-closed`)
- [x] Bestehende Sektionen in Primitive + Taxonomie umbauen, Verdrahtung 1:1 erhalten
- [x] Modell-Ordner + Sammlungs-Ordner → Sektion „Bibliothek"; Backup → „Backup & Wartung"
- [x] ADR-004 schreiben (`docs/decisions/004-einstellungen-shell.md`)
- [x] Doc-Update: `docs/routes.md` geprüft — keine Routen-Änderung

## Report-Back

Umgebaut in einem Zug: `einstellungen.ts` von flachem `settings-layout` auf `st-page` Master-Detail mit 7-Sektionen-Nav. CSS-Budget 8 kB eingehalten (kompakte Single-File-Styles, ~7,7 kB compiled). Mobile-Responsive via `:class.section-open`/`section-closed`. Alle Signals + Store-Dispatches unverändert erhalten.
