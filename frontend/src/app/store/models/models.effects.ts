import { Injectable, inject } from '@angular/core';
import { Actions, createEffect, ofType } from '@ngrx/effects';
import { catchError, map, mergeMap, switchMap } from 'rxjs';
import { of } from 'rxjs';
import type { HttpErrorResponse } from '@angular/common/http';
import { ModelService } from '@photofant/services';
import { modelsActions } from './models.actions';

@Injectable()
export class ModelsEffects {
  private readonly actions$ = inject(Actions);
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
            modelsActions.loadConfigSuccess({ modelsDir: response.data['models_dir'] ?? '' })
          ),
          catchError((error: HttpErrorResponse) =>
            of(modelsActions.loadConfigFailure({ error: error.message }))
          ),
        )
      ),
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
            modelsActions.updateModelsDirSuccess({ modelsDir: response.data['models_dir'] ?? path })
          ),
          catchError((error: HttpErrorResponse) =>
            of(modelsActions.updateModelsDirFailure({ error: error.message }))
          ),
        )
      ),
    )
  );
}
