# Phase 2 — Frontend Verarbeitungs-Einstellungen

> Rating: **standard** · Status: complete

## Kontext (vorher lesen)

- [README.md](README.md) — Kontrakt (ProcessingConfig-Interface, API-Kontrakt)
- `frontend/src/app/store/models/models.actions.ts` — `loadConfigSuccess` hat aktuell nur `{ modelsDir: string }`
- `frontend/src/app/store/models/models.effects.ts` — `loadConfig$` liest nur `response.data['models_dir']`
- `frontend/src/app/store/models/models.reducer.ts` — `ModelsState` hat nur `modelsDir`
- `frontend/src/app/services/model.service.ts` — `loadConfig()` + `updateModelsDir()`, kein generisches Patch
- `frontend/src/app/features/einstellungen/einstellungen.ts` — Inline-Template, nutzt `SettingsService` (localStorage) für Display-Settings, und `modelsActions` für models_dir; kein Bezug zu Verarbeitungs-Settings

**Hinweis:** Diese Phase supersedes `2026-06-18_einstellungen-fehlende-sektionen` Phase 1 Frontend-Seite. Wer diese Phase abschließt, kann dort die Frontend-Checkliste als erledigt markieren. Die Backend-Seite des alten Plans (import_job.py Guards, heuristics blur_threshold) ist bereits implementiert.

## ProcessingConfig-Interface

In `models.reducer.ts` definieren (export):
```ts
export interface ProcessingConfig {
  autoTag: boolean;
  autoCaption: boolean;
  autoEmbed: boolean;
  minProbability: number;
  maxTags: number;
  blurThreshold: number;
}

const PROCESSING_CONFIG_DEFAULTS: ProcessingConfig = {
  autoTag: true,
  autoCaption: true,
  autoEmbed: true,
  minProbability: 0.5,
  maxTags: 30,
  blurThreshold: 200.0,
};
```

Mapping API → ProcessingConfig (in `models.effects.ts`):
```ts
function extractProcessingConfig(data: Record<string, unknown>): ProcessingConfig {
  return {
    autoTag:        Boolean(data['auto_tag']         ?? PROCESSING_CONFIG_DEFAULTS.autoTag),
    autoCaption:    Boolean(data['auto_caption']      ?? PROCESSING_CONFIG_DEFAULTS.autoCaption),
    autoEmbed:      Boolean(data['auto_embed']        ?? PROCESSING_CONFIG_DEFAULTS.autoEmbed),
    minProbability: Number(data['min_probability']    ?? PROCESSING_CONFIG_DEFAULTS.minProbability),
    maxTags:        Number(data['max_tags']           ?? PROCESSING_CONFIG_DEFAULTS.maxTags),
    blurThreshold:  Number(data['blur_threshold']     ?? PROCESSING_CONFIG_DEFAULTS.blurThreshold),
  };
}
```

Mapping ProcessingConfig → API (in `updateProcessingConfig$` Effect):
```ts
const PROCESSING_CONFIG_KEY_MAP: Record<keyof ProcessingConfig, string> = {
  autoTag:        'auto_tag',
  autoCaption:    'auto_caption',
  autoEmbed:      'auto_embed',
  minProbability: 'min_probability',
  maxTags:        'max_tags',
  blurThreshold:  'blur_threshold',
};
```

## Checkliste

### model.service.ts

- [x] Methode `patchConfig(patch: Record<string, unknown>): Observable<ConfigResponse>` ergänzen:
  ```ts
  patchConfig(patch: Record<string, unknown>): Observable<ConfigResponse> {
    return this.http.patch<ConfigResponse>('/api/config', { data: patch });
  }
  ```
- [x] `ConfigResponse.data`-Typ von `Record<string, string | null>` auf `Record<string, unknown>` ändern (war zu eng)

### models.actions.ts

- [x] `'Load Config Success'` Props erweitern: `props<{ modelsDir: string; processingConfig: ProcessingConfig }>()`
- [x] Neue Actions:
  ```ts
  'Update Processing Config':         props<{ patch: Partial<ProcessingConfig> }>(),
  'Update Processing Config Success': props<{ processingConfig: ProcessingConfig }>(),
  'Update Processing Config Failure': props<{ error: string }>(),
  ```

### models.reducer.ts

- [x] `ProcessingConfig`-Interface + `PROCESSING_CONFIG_DEFAULTS` definieren und exportieren
- [x] `processingConfig: ProcessingConfig` zu `ModelsState` und `initialState` ergänzen (Defaults als Startzustand)
- [x] `on(modelsActions.loadConfigSuccess, ...)` um `processingConfig` erweitern
- [x] `on(modelsActions.updateProcessingConfigSuccess, ...)` ergänzen

### models.effects.ts

- [x] `loadConfig$`: `extractProcessingConfig()`-Hilfsfunktion (lokal im File), Response-Mapping anpassen
- [x] Neuer Effect `updateProcessingConfig$`

### models.selectors.ts

- [x] `selectProcessingConfig` aus `modelsFeature` destructuren und in `modelsSelectors` exportieren
- [x] `ProcessingConfig`-Type-Export in `models/index.ts` ergänzen

### einstellungen.ts — Sektion „Verarbeitung"

[x] Sektion nach der Modelle-Sektion eingefügt — alle 6 Controls mit Clamp-Handlers (`onMinProbabilityChange`, `onMaxTagsChange`, `onBlurThresholdChange`), CSS `st-number-input`, Signal `processingConfig` aus Store.

## Akzeptanzkriterien

- `loadConfigSuccess` trägt `processingConfig` — kein Compile-Fehler, Reducer setzt den State.
- `PATCH /api/config` wird bei Toggle/Input-Änderung abgefeuert; beim nächsten `GET /api/config` kommen die neuen Werte zurück.
- Einstellungen-Seite zeigt alle 6 Controls mit richtigen Defaults.

## Report-Back
