# Phase 3 — BEM-Bereinigung + Parent aufräumen

## Kontext

Zu lesen:
- Alle 7 Child-Komponenten-Templates (aus Phase 2) — dort sind noch die alten `st-`/`sp-`/`sc-`-Präfixe aus dem ursprünglichen Inline-Template
- `einstellungen.html` + `einstellungen.scss` — Shell-Klassen ebenfalls noch mit alten Präfixen

Phase 3 bereinigt alle CSS-Klassen auf BEM nach Selektor und stellt sicher dass die Shell wirklich nur noch Navigation enthält.

## Umbenennungs-Mapping (Shell)

| Alt | Neu (BEM) | Komponente |
|---|---|---|
| `.st-nav` | `einstellungen__nav` | Shell-SCSS |
| `.st-nav-title` | `einstellungen__nav-title` | Shell |
| `.st-nav-item` | `einstellungen__nav-item` | Shell |
| `.st-nav-item.on` | `einstellungen__nav-item--aktiv` | Shell |
| `.st-nav-ico` | `einstellungen__nav-icon` | Shell |
| `.st-nav-back` | `einstellungen__nav-back` | Shell |
| `.st-body` | `einstellungen__body` | Shell |
| `.section-open` / `.section-closed` | `einstellungen__nav--offen` / `einstellungen__body--verborgen` | Shell |

## Umbenennungs-Mapping (shared Section-Primitive)

Diese Klassen werden innerhalb der Child-Komponenten verwendet. Jede Child-Komponente bekommt eigene BEM-Klassen nach ihrem Selektor. Gemeinsame Muster (Row, Group, Note, Btn) werden konsistent benannt:

| Alt | Neu (Muster, Block = Selektor der Child-Komponente) | Gilt in |
|---|---|---|
| `.st-section` | `:host` (entfällt als Klasse) | alle Child-Komponenten |
| `.st-section-head` | `<block>__kopf` | alle Child-Komponenten |
| `.st-group-label` | `<block>__gruppen-label` | zutreffende |
| `.st-group` | `<block>__gruppe` | alle |
| `.st-row` | `<block>__zeile` | alle |
| `.st-row.top` | `<block>__zeile--oben` | alle |
| `.st-row-body` | `<block>__zeile-inhalt` | alle |
| `.st-row-title` | `<block>__zeile-titel` | alle |
| `.st-row-sub` | `<block>__zeile-sub` | alle |
| `.st-row-ctrl` | `<block>__zeile-steuerung` | alle |
| `.st-btn` | `<block>__schaltfläche` | alle |
| `.st-btn.accent` / `.ghost` / `.danger` | `<block>__schaltfläche--akzent` etc. | alle |
| `.st-switch` | `<block>__schalter` | Verarbeitung, Darstellung |
| `.st-switch.on` | `<block>__schalter--an` | |
| `.st-select` | `<block>__auswahl` | Darstellung |
| `.st-num` | `<block>__zahleneingabe` | Verarbeitung |
| `.st-note` | `<block>__hinweis` | alle |
| `.st-note.warn/.accent/.info` | `<block>__hinweis--warn` etc. | |
| `.st-key` | `tastaturkuerzel__taste` | Tastaturkürzel |
| `.st-sc-row` | `tastaturkuerzel__zeile` | Tastaturkürzel |
| `.st-sc-row.editing` | `tastaturkuerzel__zeile--aktiv` | Tastaturkürzel |
| `.st-sc-action` | `tastaturkuerzel__aktion` | Tastaturkürzel |
| `.st-sc-keys` | `tastaturkuerzel__tasten` | Tastaturkürzel |
| `.st-sc-listening` | `tastaturkuerzel__warte-hinweis` | Tastaturkürzel |
| `.st-path` | `bibliothek__pfad` | Bibliothek |
| `.sp-val` | `bibliothek__pfad-wert` | Bibliothek |
| `.sp-btn` | `bibliothek__pfad-ändern` | Bibliothek |
| `.path-edit` | `bibliothek__pfad-edit` | Bibliothek |
| `.dir-input` | `bibliothek__pfad-eingabe` | Bibliothek |

🟡 Das sind viele Umbennungen. Systematisch vorgehen: erst Shell, dann Komponente für Komponente. `ng serve` nach jeder Komponente kurz prüfen — visuelle Regressions sind sofort sichtbar.

## Akzeptanzkriterien

- Kein `st-`, `sp-`, `sc-`-, `.on`-, `.editing`-Klasse (als nackter Modifier ohne Block) mehr in irgendeinem Template
- Alle Klassen sind BEM-konform und unmittelbar lesbar ohne SCSS zu öffnen
- `einstellungen.ts` hat keine sektionsspezifischen Felder oder Methoden mehr
- Shell-SCSS enthält ausschließlich Klassen für die Navigation-Hülle
- `ng build` fehlerfrei, visuell identisch zur Ausgangssituation

## Checkliste

### Implementation

- [x] Shell (`einstellungen.html` / `einstellungen.scss`) — alle Klassen nach Mapping umbenennen
- [x] `bibliothek` — Klassen umbenennen, SCSS anpassen
- [x] `verarbeitung` — Klassen umbenennen, SCSS anpassen
- [x] `darstellung` — Klassen umbenennen, SCSS anpassen
- [x] `bearbeitung` — Klassen umbenennen, SCSS anpassen
- [x] `tastaturkuerzel` — Klassen umbenennen, SCSS anpassen
- [x] `backup-wartung` — Klassen umbenennen, SCSS anpassen
- [x] `info` — Klassen umbenennen, SCSS anpassen
- [x] Grep auf `st-`, `sp-val`, `sp-btn`, `sc-` — kein Treffer mehr in `features/einstellungen/`
- [x] `ng build` fehlerfrei

### Docs

- [x] Keine Doc-Updates nötig

## Report-Back

Phase 3 complete (2026-06-19).

- Shell: `st-*` → `einstellungen__*`; `.on`/`.section-open`/`.section-closed` → BEM-Modifier
- 8 Child-Komponenten: outer `<div class="st-section">` entfernt (`:host` übernimmt), alle `st-*`/`sp-*`/`sc-*` → komponentenspezifisches BEM (`bibliothek__*`, `verarbeitung__*`, …)
- `_st-shared.scss`: auf Utilities ohne `st-`-Präfix getrimmt (`code`, `.spinner`, `.group-loading`, `.group-empty`, `.error-banner`)
- Inline-Styles entfernt: `bearbeitung` (Preset-Buttons → `--klein`-Modifier), `tags` (Listenheader → `tags-list-head__anzahl`/`__alias`)
- `ng build` grün; Budget-Warning in `tags.scss` (5.6 KB > 4 KB) war vorher schon da — kein Regression
