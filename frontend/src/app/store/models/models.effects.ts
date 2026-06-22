import { Injectable, inject } from '@angular/core';
import { Actions, createEffect, ofType } from '@ngrx/effects';
import { Store } from '@ngrx/store';
import { concatLatestFrom } from '@ngrx/operators';
import { catchError, EMPTY, from, map, mergeMap, of, switchMap } from 'rxjs';
import type { HttpErrorResponse } from '@angular/common/http';
import type { ProcessingConfig, ShortcutConfig } from '@photofant/models';
import { PROCESSING_CONFIG_DEFAULTS } from '@photofant/models';
import { ModelService } from '@photofant/services';
import { jobsActions } from '../jobs/jobs.actions';
import { modelsActions } from './models.actions';
import { modelsSelectors } from './models.selectors';

const PROCESSING_CONFIG_KEY_MAP: Record<keyof ProcessingConfig, string> = {
  autoTag:             'auto_tag',
  autoCaption:         'auto_caption',
  autoEmbed:           'auto_embed',
  minProbability:      'min_probability',
  maxTags:             'max_tags',
  blurThreshold:       'blur_threshold',
  dupeThreshold:       'dupe_threshold',
  faceAutoThreshold:   'face_auto_threshold',
  faceReviewThreshold: 'face_review_threshold',
  faceMinClusterSize:  'face_min_cluster_size',
};

function extractProcessingConfig(data: Record<string, unknown>): ProcessingConfig {
  return {
    autoTag:             Boolean(data['auto_tag']              ?? PROCESSING_CONFIG_DEFAULTS.autoTag),
    autoCaption:         Boolean(data['auto_caption']          ?? PROCESSING_CONFIG_DEFAULTS.autoCaption),
    autoEmbed:           Boolean(data['auto_embed']            ?? PROCESSING_CONFIG_DEFAULTS.autoEmbed),
    minProbability:      Number(data['min_probability']        ?? PROCESSING_CONFIG_DEFAULTS.minProbability),
    maxTags:             Number(data['max_tags']               ?? PROCESSING_CONFIG_DEFAULTS.maxTags),
    blurThreshold:       Number(data['blur_threshold']         ?? PROCESSING_CONFIG_DEFAULTS.blurThreshold),
    dupeThreshold:       Number(data['dupe_threshold']         ?? PROCESSING_CONFIG_DEFAULTS.dupeThreshold),
    faceAutoThreshold:   Number(data['face_auto_threshold']    ?? PROCESSING_CONFIG_DEFAULTS.faceAutoThreshold),
    faceReviewThreshold: Number(data['face_review_threshold']  ?? PROCESSING_CONFIG_DEFAULTS.faceReviewThreshold),
    faceMinClusterSize:  Number(data['face_min_cluster_size']  ?? PROCESSING_CONFIG_DEFAULTS.faceMinClusterSize),
  };
}

function extractShortcutConfig(data: Record<string, unknown>): ShortcutConfig | null {
  const raw = data['keyboard_shortcuts'];
  if (raw == null || typeof raw !== 'object' || Array.isArray(raw)) { return null; }
  const obj = raw as Record<string, unknown>;
  if (!Array.isArray(obj['shortcuts'])) { return null; }
  return raw as ShortcutConfig;
}

@Injectable()
export class ModelsEffects {
  private readonly actions$ = inject(Actions);
  private readonly store = inject(Store);
  private readonly modelService = inject(ModelService);

  readonly loadModels$ = createEffect(() =>
    this.actions$.pipe(
      ofType(modelsActions.loadModels),
      switchMap(() =>
        this.modelService.loadModels().pipe(
          map((models) => modelsActions.loadModelsSuccess({ models })),
          catchError((error: HttpErrorResponse) =>
            of(modelsActions.loadModelsFailure({ error: error.message }))
          ),
        )
      ),
    )
  );

  readonly loadCapabilities$ = createEffect(() =>
    this.actions$.pipe(
      ofType(modelsActions.loadCapabilities),
      switchMap(() =>
        this.modelService.loadCapabilities().pipe(
          map((capabilities) => modelsActions.loadCapabilitiesSuccess({ capabilities })),
          catchError((error: HttpErrorResponse) =>
            of(modelsActions.loadCapabilitiesFailure({ error: error.message }))
          ),
        )
      ),
    )
  );

  readonly loadConfig$ = createEffect(() =>
    this.actions$.pipe(
      ofType(modelsActions.loadConfig),
      switchMap(() =>
        this.modelService.loadConfig().pipe(
          map((response) =>
            modelsActions.loadConfigSuccess({
              modelsDir: String(response.data['models_dir'] ?? ''),
              dataRoot: response.data['data_root'] != null ? String(response.data['data_root']) : null,
              processingConfig: extractProcessingConfig(response.data),
              keyboardShortcuts: extractShortcutConfig(response.data),
            })
          ),
          catchError((error: HttpErrorResponse) =>
            of(modelsActions.loadConfigFailure({ error: error.message }))
          ),
        )
      ),
    )
  );

  readonly updateShortcuts$ = createEffect(() =>
    this.actions$.pipe(
      ofType(modelsActions.updateShortcuts),
      switchMap(({ config }) =>
        this.modelService.patchConfig({ keyboard_shortcuts: config }).pipe(
          map((response) =>
            modelsActions.updateShortcutsSuccess({
              config: extractShortcutConfig(response.data),
            })
          ),
          catchError((error: HttpErrorResponse) =>
            of(modelsActions.updateShortcutsFailure({ error: error.message }))
          ),
        )
      ),
    )
  );

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

  readonly downloadModel$ = createEffect(() =>
    this.actions$.pipe(
      ofType(modelsActions.downloadModel),
      mergeMap(({ manifestId, licenseAck }) =>
        this.modelService.downloadModel(manifestId, licenseAck).pipe(
          map((response) =>
            modelsActions.downloadModelSuccess({ jobId: response.job_id, manifestId })
          ),
          catchError((error: HttpErrorResponse) =>
            of(modelsActions.downloadModelFailure({ manifestId, error: error.message }))
          ),
        )
      ),
    )
  );

  // Watch SSE job updates: reload models on success, surface error on failure
  readonly watchDownloadJobUpdates$ = createEffect(() =>
    this.actions$.pipe(
      ofType(jobsActions.upsertJob),
      concatLatestFrom(() => this.store.select(modelsSelectors.selectDownloadJobIds)),
      mergeMap(([{ job }, downloadJobIds]) => {
        if (job.kind !== 'download_model') return EMPTY;
        if (job.state !== 'done' && job.state !== 'error') return EMPTY;

        const entry = Object.entries(downloadJobIds).find(([, jobId]) => jobId === job.id);
        if (entry === undefined) return EMPTY;

        const [manifestId] = entry;

        if (job.state === 'done') {
          return from([
            modelsActions.downloadJobCompleted({ manifestId }),
            modelsActions.loadModels(),
          ]);
        }

        return of(modelsActions.downloadJobFailed({
          manifestId,
          error: job.error ?? 'Download fehlgeschlagen',
        }));
      }),
    )
  );

  readonly registerLocal$ = createEffect(() =>
    this.actions$.pipe(
      ofType(modelsActions.registerLocal),
      switchMap(({ manifestId, path }) =>
        this.modelService.registerLocal(manifestId, path).pipe(
          map((model) => modelsActions.registerLocalSuccess({ model })),
          catchError((error: HttpErrorResponse) => {
            const detail = error.error as { code?: string } | null;
            return of(modelsActions.registerLocalFailure({
              manifestId,
              error: error.message,
              code: detail?.code ?? 'UNKNOWN',
            }));
          }),
        )
      ),
    )
  );

  readonly deleteModel$ = createEffect(() =>
    this.actions$.pipe(
      ofType(modelsActions.deleteModel),
      switchMap(({ manifestId }) =>
        this.modelService.deleteModel(manifestId).pipe(
          map(() => modelsActions.deleteModelSuccess({ manifestId })),
          catchError((error: HttpErrorResponse) =>
            of(modelsActions.deleteModelFailure({ error: error.message }))
          ),
        )
      ),
    )
  );

  readonly updateModelsDir$ = createEffect(() =>
    this.actions$.pipe(
      ofType(modelsActions.updateModelsDir),
      switchMap(({ path }) =>
        this.modelService.updateModelsDir(path).pipe(
          map((response) =>
            modelsActions.updateModelsDirSuccess({ modelsDir: String(response.data['models_dir'] ?? path) })
          ),
          catchError((error: HttpErrorResponse) =>
            of(modelsActions.updateModelsDirFailure({ error: error.message }))
          ),
        )
      ),
    )
  );

  readonly updateDataRoot$ = createEffect(() =>
    this.actions$.pipe(
      ofType(modelsActions.updateDataRoot),
      switchMap(({ path }) =>
        this.modelService.updateDataRoot(path).pipe(
          map((response) =>
            modelsActions.updateDataRootSuccess({ dataRoot: String(response.data['data_root'] ?? path) })
          ),
          catchError((error: HttpErrorResponse) =>
            of(modelsActions.updateDataRootFailure({ error: error.message }))
          ),
        )
      ),
    )
  );
}
