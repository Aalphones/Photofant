# Phase 2 — Child-Komponenten via ng generate

## Kontext

Zu lesen:
- `frontend/src/app/features/einstellungen/einstellungen.ts` — Quelle aller zu verschiebenden Signals/Methoden
- `frontend/src/app/features/einstellungen/einstellungen.html` — Quelle der Section-Templates (aus Phase 1)
- `docs/conventions/angular.md` falls vorhanden, sonst `lang-angular` Skill

Alle 7 Child-Komponenten werden mit `ng generate component` angelegt (im `frontend/`-Verzeichnis, wo `angular.json` liegt). Jede Komponente bekommt ihre Section-Logik aus der Shell — Shell verliert alles außer Navigation.

## ng generate Befehle

```bash
ng generate component features/einstellungen/bibliothek --skip-tests
ng generate component features/einstellungen/verarbeitung --skip-tests
ng generate component features/einstellungen/darstellung --skip-tests
ng generate component features/einstellungen/bearbeitung --skip-tests
ng generate component features/einstellungen/tastaturkuerzel --skip-tests
ng generate component features/einstellungen/backup-wartung --skip-tests
ng generate component features/einstellungen/info --skip-tests
```

## Logik-Zuordnung (Shell → Child)

### `bibliothek/`
Signals: `dataRoot`, `rebootRequired`, `modelsDir`, `isDataRootEditing`, `pendingDataRoot`, `isDirEditing`, `pendingDir`
Methoden: `startDataRootEdit`, `cancelDataRootEdit`, `saveDataRootEdit`, `startDirEdit`, `cancelDirEdit`, `saveDirEdit`
Store: `modelsSelectors.selectDataRoot`, `.selectRebootRequired`, `.selectModelsDir`; `modelsActions.updateDataRoot`, `.updateModelsDir`, `.loadConfig`
Load-Dispatch: `modelsActions.loadConfig()` im constructor-`effect()`

### `verarbeitung/`
Signals: `processingConfig` (via `store.selectSignal(modelsSelectors.selectProcessingConfig)`)
Methoden: `patchProcessingConfig`, `onMinProbabilityChange`, `onMaxTagsChange`, `onBlurThresholdChange`
Store: `modelsSelectors.selectProcessingConfig`; `modelsActions.updateProcessingConfig`
Load-Dispatch: `modelsActions.loadConfig()` im constructor-`effect()`

### `darstellung/`
Signals: `displaySettings` (via `inject(SettingsService).snapshot`)
Methoden: `setShowMeta`, `setReducedMotion`, `setLocale`, `setDateFormat`
DI: `SettingsService`, `Store` (für `filtersActions.setDensity`)

### `bearbeitung/`
Signals: `presets`, `isLoadingPresets`, `showPresetDialog`, `editingPreset`, `captionerModel`, `captionerCapabilities`
Methoden: `openCreateDialog`, `openEditDialog`, `closePresetDialog`, `onPresetSave`, `setDefault`, `deletePreset`, `presetSummary`
Store: `presetsSelectors.*`, `modelsSelectors.selectModels`; `presetsActions.*`
Load-Dispatch: `presetsActions.loadPresets()` + `modelsActions.loadModels()` im constructor-`effect()`
Imports: `PresetDialog`, `Icon`

### `tastaturkuerzel/`
Signals: `listeningAction`, `resolvedShortcuts` (via `inject(ShortcutService).resolvedShortcuts`)
Methoden: `startListening`, `applyCapture` (private), `resetShortcuts`, `formatKeys`
DI: `ShortcutService`, `DestroyRef`, `DOCUMENT` (für keydown-Listener)
Const: `SHORTCUT_ROWS` aus `einstellungen.types`
🟡 Der globale `keydown`-Listener wandert mit in diese Komponente — er ist nur für Shortcuts relevant, gehört also hier rein, nicht in die Shell.

### `backup-wartung/`
Signals: `backups`, `isLoadingBackups`, `isRunningBackup`, `error`
Methoden: `triggerBackup`, `refreshBackups`
Store: `maintenanceSelectors.*`; `maintenanceActions.triggerBackup`, `.loadBackups`
Imports: `DatePipe`
Load-Dispatch: `maintenanceActions.loadBackups()` im constructor-`effect()`

### `info/`
Signals: `appInfo`, `isLoadingAppInfo`
Methoden: `formatSize`, `objectKeys` (als `readonly objectKeys = Object.keys`)
Store: `maintenanceSelectors.selectAppInfo`, `.selectIsLoadingAppInfo`
Load-Dispatch: `maintenanceActions.loadAppInfo()` im constructor-`effect()`

## Akzeptanzkriterien

- Alle 7 Unterordner existieren, je mit `.ts` + `.html` + `.scss` (via CLI angelegt)
- Jede Komponente hat `ChangeDetectionStrategy.OnPush`
- Jede Komponente trägt ihre Load-Actions selbst (kein Load-Dispatch mehr in der Shell)
- `einstellungen.html` `@switch` verweist auf die echten Child-Tags (kein Platzhalter-Kommentar mehr)
- `einstellungen.ts` importiert nur noch die 7 Child-Komponenten, keine Store-Selektoren mehr (außer für Navigation falls nötig)
- `ng build` fehlerfrei

## Checkliste

### Implementation

- [x] `ng generate` Befehle ausführen (alle 8 inkl. tags, im `frontend/`-Verzeichnis)
- [x] `bibliothek` — Template + Logik aus Shell übernehmen; BEM-Klassen nach `bibliothek__*`
- [x] `verarbeitung` — Template + Logik aus Shell übernehmen; BEM-Klassen nach `verarbeitung__*`
- [x] `darstellung` — Template + Logik aus Shell übernehmen; BEM-Klassen nach `darstellung__*`
- [x] `bearbeitung` — Template + Logik + PresetDialog aus Shell übernehmen; BEM-Klassen nach `bearbeitung__*`
- [x] `tastaturkuerzel` — Template + Logik + keydown-Listener aus Shell übernehmen; BEM-Klassen nach `tastaturkuerzel__*`
- [x] `backup-wartung` — Template + Logik aus Shell übernehmen; BEM-Klassen nach `backup-wartung__*`
- [x] `info` — Template + Logik aus Shell übernehmen; BEM-Klassen nach `info__*`
- [x] `tags` — Template + Logik + TagMergeDialog aus Shell übernehmen (nicht im ursprünglichen Plan, aber SECTIONS enthält 8 Sektionen)
- [x] `einstellungen.html` `@switch` auf Child-Tags umstellen
- [x] Child-Komponenten in `einstellungen.ts` importieren; Shell-Logik entfernen
- [x] `ng build` fehlerfrei

### Docs

- [x] Keine Doc-Updates nötig

## Report-Back

- 8 Child-Komponenten angelegt (1 mehr als geplant: `tags` war in SECTIONS vorhanden)
- PresetDialog aus `einstellungen.html` in `bearbeitung.html` verschoben
- TagMergeDialog aus `einstellungen.html` in `tags.html` verschoben
- `_st-shared.scss` angelegt: gemeinsame `st-*` Utility-Styles, die alle Child-Komponenten via `@use '../st-shared' as *` einbinden (Angular ViewEncapsulation verhindert dass Parent-Styles in Child-Templates wirken)
- `einstellungen.ts` reduziert auf Navigation: `sections`, `activeSection`, `mobileOpen`, `goSection()`, `goBack()`
- `einstellungen.scss` auf Nav/Shell-Styles reduziert
