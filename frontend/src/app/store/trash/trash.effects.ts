import { Injectable, inject } from '@angular/core';
import { Actions, createEffect, ofType } from '@ngrx/effects';
import { catchError, map, mergeMap, of, switchMap } from 'rxjs';
import type { HttpErrorResponse } from '@angular/common/http';
import type { AssetDto } from '@photofant/models';
import { AssetService } from '@photofant/services';
import { trashActions } from './trash.actions';

@Injectable()
export class TrashEffects {
  private readonly actions$ = inject(Actions);
  private readonly assetService = inject(AssetService);

  readonly load$ = createEffect(() =>
    this.actions$.pipe(
      ofType(trashActions.load),
      switchMap(() =>
        this.assetService.listTrash().pipe(
          map((items: AssetDto[]) => trashActions.loadSuccess({ items })),
          catchError((error: HttpErrorResponse) =>
            of(trashActions.loadFailure({ error: error.message }))
          ),
        )
      ),
    )
  );

  readonly restore$ = createEffect(() =>
    this.actions$.pipe(
      ofType(trashActions.restore),
      mergeMap(({ id }) =>
        this.assetService.restoreAsset(id).pipe(
          map(() => trashActions.restoreSuccess({ id })),
          catchError((error: HttpErrorResponse) =>
            of(trashActions.restoreFailure({ error: error.message }))
          ),
        )
      ),
    )
  );

  readonly purge$ = createEffect(() =>
    this.actions$.pipe(
      ofType(trashActions.purge),
      mergeMap(({ id }) =>
        this.assetService.purgeAsset(id).pipe(
          map(() => trashActions.purgeSuccess({ id })),
          catchError((error: HttpErrorResponse) =>
            of(trashActions.purgeFailure({ error: error.message }))
          ),
        )
      ),
    )
  );

  readonly empty$ = createEffect(() =>
    this.actions$.pipe(
      ofType(trashActions.empty),
      switchMap(() =>
        this.assetService.emptyTrash().pipe(
          map(() => trashActions.emptySuccess()),
          catchError((error: HttpErrorResponse) =>
            of(trashActions.emptyFailure({ error: error.message }))
          ),
        )
      ),
    )
  );
}
