# Phase 2 — Frontend Verarbeitungs-Einstellungen

> Rating: **standard** · Status: pending

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

- [ ] Methode `patchConfig(patch: Record<string, unknown>): Observable<ConfigResponse>` ergänzen:
  ```ts
  patchConfig(patch: Record<string, unknown>): Observable<ConfigResponse> {
    return this.http.patch<ConfigResponse>('/api/config', { data: patch });
  }
  ```
- [ ] `ConfigResponse.data`-Typ von `Record<string, string | null>` auf `Record<string, unknown>` ändern (war zu eng)

### models.actions.ts

- [ ] `'Load Config Success'` Props erweitern: `props<{ modelsDir: string; processingConfig: ProcessingConfig }>()`
- [ ] Neue Actions:
  ```ts
  'Update Processing Config':         props<{ patch: Partial<ProcessingConfig> }>(),
  'Update Processing Config Success': props<{ processingConfig: ProcessingConfig }>(),
  'Update Processing Config Failure': props<{ error: string }>(),
  ```

### models.reducer.ts

- [ ] `ProcessingConfig`-Interface + `PROCESSING_CONFIG_DEFAULTS` definieren und exportieren
- [ ] `processingConfig: ProcessingConfig` zu `ModelsState` und `initialState` ergänzen (Defaults als Startzustand)
- [ ] `on(modelsActions.loadConfigSuccess, ...)` um `processingConfig` erweitern:
  ```ts
  on(modelsActions.loadConfigSuccess, (state, { modelsDir, processingConfig }) =>
    ({ ...state, modelsDir, processingConfig })
  )
  ```
- [ ] `on(modelsActions.updateProcessingConfigSuccess, ...)` ergänzen

### models.effects.ts

- [ ] `loadConfig$`: `extractProcessingConfig()`-Hilfsfunktion (lokal im File), Response-Mapping anpassen:
  ```ts
  map((response) => modelsActions.loadConfigSuccess({
    modelsDir: response.data['models_dir'] as string ?? '',
    processingConfig: extractProcessingConfig(response.data),
  }))
  ```
- [ ] Neuer Effect `updateProcessingConfig$`:
  ```ts
  readonly updateProcessingConfig$ = createEffect(() =>
    this.actions$.pipe(
      ofType(modelsActions.updateProcessingConfig),
      switchMap(({ patch }) => {
        const apiPatch: Record<string, unknown> = {};
        for (const [key, value] of Object.entries(patch)) {
          const apiKey = PROCESSING_CONFIG_KEY_MAP[key as keyof ProcessingConfig];
          if (apiKey !== undefined) { apiPatch[apiKey] = value; }
        }
        return this.modelService.patchConfig(apiPatch).pipe(
          map((response) => modelsActions.updateProcessingConfigSuccess({
            processingConfig: extractProcessingConfig(response.data),
          })),
          catchError((error: HttpErrorResponse) =>
            of(modelsActions.updateProcessingConfigFailure({ error: error.message }))
          ),
        );
      }),
    )
  );
  ```

### models.selectors.ts

- [ ] `selectProcessingConfig` aus `modelsFeature` destructuren und in `modelsSelectors` exportieren
- [ ] `ProcessingConfig`-Type-Export in `models/index.ts` ergänzen

### einstellungen.ts — Sektion „Verarbeitung"

Sektion nach der Modelle-Sektion einfügen. Controls:

| Einstellung | Control | Wert |
|---|---|---|
| auto_tag | Toggle-Switch | bool |
| auto_caption | Toggle-Switch | bool |
| auto_embed | Toggle-Switch | bool |
| min_probability | `<input type="number" min="0" max="1" step="0.05">` | float |
| max_tags | `<input type="number" min="1" max="200">` | int |
| blur_threshold | `<input type="number" min="0" max="1000" step="10">` | float |

Label-Texte:
- auto_tag: „Auto-Tagging (WD14)" / „Beim Import automatisch WD14-Tags generieren."
- auto_caption: „Auto-Caption (Florence-2)" / „Beim Import automatisch Bildbeschreibungen generieren."
- auto_embed: „CLIP-Embedding" / „Beim Import automatisch semantische Suchdaten berechnen."
- min_probability: „Mindest-Konfidenz (WD14)" / „Tags unterhalb dieses Wertes werden verworfen. Default: 0.5"
- max_tags: „Max. Tags pro Bild" / „Maximale Anzahl automatisch gesetzter Tags, nach Konfidenz sortiert. Default: 30"
- blur_threshold: „Mindestschärfe (Laplacian-Varianz)" / „Bilder unterhalb gelten als unscharf. Default: 200"

Änderungen dispatchen via:
```ts
this.store.dispatch(modelsActions.updateProcessingConfig({ patch: { autoTag: value } }));
```

Werte aus Store lesen:
```ts
readonly processingConfig = this.store.selectSignal(modelsSelectors.selectProcessingConfig);
```
Constructor: `this.store.dispatch(modelsActions.loadConfig())` (bereits vorhanden).

🟡 **Float-Input UX:** `min_probability` sollte bei `blur` clamp auf `[0, 1]` prüfen; `max_tags` auf `[1, 200]`. Im Template via `(blur)="clampMinProbability($event)"` o.ä. — kein separates Validierungs-Framework nötig.

## Akzeptanzkriterien

- `loadConfigSuccess` trägt `processingConfig` — kein Compile-Fehler, Reducer setzt den State.
- `PATCH /api/config` wird bei Toggle/Input-Änderung abgefeuert; beim nächsten `GET /api/config` kommen die neuen Werte zurück.
- Einstellungen-Seite zeigt alle 6 Controls mit richtigen Defaults.

## Report-Back
