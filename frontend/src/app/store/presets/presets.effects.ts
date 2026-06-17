import { Injectable, inject } from '@angular/core';
import { Actions, createEffect, ofType } from '@ngrx/effects';
import { catchError, map, mergeMap, switchMap } from 'rxjs';
import { of } from 'rxjs';
import type { HttpErrorResponse } from '@angular/common/http';
import { CaptionPresetService } from '@photofant/services';
import { presetsActions } from './presets.actions';

@Injectable()
export class PresetsEffects {
  private readonly actions$ = inject(Actions);
  private readonly presetService = inject(CaptionPresetService);

  readonly loadPresets$ = createEffect(() =>
    this.actions$.pipe(
      ofType(presetsActions.loadPresets),
      switchMap(() =>
        this.presetService.list().pipe(
          map((presets) => presetsActions.loadPresetsSuccess({ presets })),
          catchError((error: HttpErrorResponse) =>
            of(presetsActions.loadPresetsFailure({ error: error.message }))
          ),
        )
      ),
    )
  );

  readonly createPreset$ = createEffect(() =>
    this.actions$.pipe(
      ofType(presetsActions.createPreset),
      mergeMap(({ body }) =>
        this.presetService.create(body).pipe(
          map((preset) => presetsActions.createPresetSuccess({ preset })),
          catchError((error: HttpErrorResponse) =>
            of(presetsActions.createPresetFailure({ error: error.message }))
          ),
        )
      ),
    )
  );

  readonly updatePreset$ = createEffect(() =>
    this.actions$.pipe(
      ofType(presetsActions.updatePreset),
      mergeMap(({ id, body }) =>
        this.presetService.update(id, body).pipe(
          map((preset) => presetsActions.updatePresetSuccess({ preset })),
          catchError((error: HttpErrorResponse) =>
            of(presetsActions.updatePresetFailure({ error: error.message }))
          ),
        )
      ),
    )
  );

  readonly deletePreset$ = createEffect(() =>
    this.actions$.pipe(
      ofType(presetsActions.deletePreset),
      mergeMap(({ id }) =>
        this.presetService.delete(id).pipe(
          map(() => presetsActions.deletePresetSuccess({ id })),
          catchError((error: HttpErrorResponse) =>
            of(presetsActions.deletePresetFailure({ error: error.message }))
          ),
        )
      ),
    )
  );
}
