import { Injectable, inject } from '@angular/core';
import { Actions, createEffect, ofType } from '@ngrx/effects';
import { catchError, map, of, switchMap } from 'rxjs';
import type { HttpErrorResponse } from '@angular/common/http';
import { ComfyUIService } from '@photofant/services';
import { comfyuiActions } from './comfyui.actions';

@Injectable()
export class ComfyUIEffects {
  private readonly actions$ = inject(Actions);
  private readonly comfyuiService = inject(ComfyUIService);

  readonly loadConfig$ = createEffect(() =>
    this.actions$.pipe(
      ofType(comfyuiActions.loadConfig),
      switchMap(() =>
        this.comfyuiService.loadConfig().pipe(
          map((config) => comfyuiActions.loadConfigSuccess({ config })),
          catchError((error: HttpErrorResponse) =>
            of(comfyuiActions.loadConfigFailure({ error: error.message }))
          ),
        )
      ),
    )
  );

  readonly saveConfig$ = createEffect(() =>
    this.actions$.pipe(
      ofType(comfyuiActions.saveConfig),
      switchMap(({ config }) =>
        this.comfyuiService.saveConfig(config).pipe(
          map((saved) => comfyuiActions.saveConfigSuccess({ config: saved })),
          catchError((error: HttpErrorResponse) =>
            of(comfyuiActions.saveConfigFailure({ error: error.message }))
          ),
        )
      ),
    )
  );

  readonly testConnection$ = createEffect(() =>
    this.actions$.pipe(
      ofType(comfyuiActions.testConnection),
      switchMap(() =>
        this.comfyuiService.testConnection().pipe(
          map(({ ok, detail }) => comfyuiActions.testConnectionSuccess({ ok, detail })),
          catchError((error: HttpErrorResponse) =>
            of(comfyuiActions.testConnectionFailure({ error: error.message }))
          ),
        )
      ),
    )
  );
}
