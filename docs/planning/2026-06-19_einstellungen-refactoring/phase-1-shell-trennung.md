# Phase 1 — Shell-Trennung: HTML / SCSS / Types auslagern

## Kontext

Zu lesen:
- `frontend/src/app/features/einstellungen/einstellungen.ts` — die zu zerlegende Datei (970 Zeilen)
- `docs/conventions/angular.md` falls vorhanden, sonst `lang-angular` Skill

Die Shell `einstellungen.ts` existiert bereits — `ng generate` kann sie nicht neu anlegen. Phase 1 legt die fehlenden Dateien manuell an und bereinigt die `.ts`-Datei. Phase 2 übernimmt dann den echten `ng generate`-Einsatz für die Child-Komponenten.

## Akzeptanzkriterien

- `einstellungen.html` existiert mit dem Shell-Inhalt (Nav-Aside + `@switch` mit Platzhalter-Kommentaren für die Child-Tags, die Phase 2 einsetzt)
- `einstellungen.scss` existiert mit dem Shell-spezifischen CSS (Nav, Body, Responsive — alles was die Shell-Hülle betrifft; Section-spezifisches CSS fliegt raus)
- `einstellungen.types.ts` existiert mit `Section` und `ShortcutRow` (plain exports, keine Klasse)
- `einstellungen.ts` hat `templateUrl: './einstellungen.html'` und `styleUrl: './einstellungen.scss'` — kein `template:`, kein `styles:`
- `einstellungen.ts` importiert `Section` und `ShortcutRow` aus `./einstellungen.types`
- Die Datei kompiliert fehlerfrei (`ng build` / `ng serve`)

## Checkliste

### Implementation

- [ ] `einstellungen.types.ts` schreiben: `Section` Interface + `ShortcutRow` Interface exportieren; `SECTIONS` und `SHORTCUT_ROWS` const-Arrays ebenfalls exportieren
- [ ] `einstellungen.html` anlegen: Inhalt aus `template: \`…\`` übernehmen; `@switch`-Cases mit `<!-- TODO Phase 2: <pf-xxx /> -->` Kommentar versehen statt vollständigem Inhalt (der kommt in Phase 2 in die Child-Komponenten)
- [ ] `einstellungen.scss` anlegen: Shell-CSS aus `styles: [\`…\`]` übernehmen — nur die Klassen die zur Shell-Hülle gehören: `:host`, `.st-nav*`, `.st-body`, `.st-nav-back`, `.path-edit`, `.dir-input`, `.st-path`, `.sp-val`, `.sp-btn`, sowie `@media`-Query; Section-interne Klassen wie `.presets-list`, `.backup-row`, `.info-grid`, `.st-sc-*` etc. bleiben vorerst hier (werden in Phase 3 in Child-SCSS verschoben)
- [ ] `einstellungen.ts` anpassen: `template: \`…\`` → `templateUrl: './einstellungen.html'`; `styles: [\`…\`]` → `styleUrl: './einstellungen.scss'`; Interface-Inline-Deklarationen entfernen; Import aus `./einstellungen.types` ergänzen
- [ ] `ng build` / `ng serve` — fehlerfrei

### Docs

- [ ] Keine Doc-Updates nötig (rein internes Refactoring)

## Report-Back
