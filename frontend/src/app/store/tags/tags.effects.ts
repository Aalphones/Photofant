import { Injectable, inject } from '@angular/core';
import { Actions, createEffect, ofType } from '@ngrx/effects';
import { catchError, map, mergeMap, of, switchMap } from 'rxjs';
import type { HttpErrorResponse } from '@angular/common/http';
import type { TagListItem } from '@photofant/models';
import { TagService } from '@photofant/services';
import { tagsActions } from './tags.actions';

@Injectable()
export class TagsEffects {
  private readonly actions$ = inject(Actions);
  private readonly tagService = inject(TagService);

  readonly load$ = createEffect(() =>
    this.actions$.pipe(
      ofType(tagsActions.load),
      switchMap(() =>
        this.tagService.listAllTags().pipe(
          map((items: TagListItem[]) => tagsActions.loadSuccess({ items })),
          catchError((error: HttpErrorResponse) =>
            of(tagsActions.loadFailure({ error: error.message }))
          ),
        )
      ),
    )
  );

  readonly rename$ = createEffect(() =>
    this.actions$.pipe(
      ofType(tagsActions.rename),
      mergeMap(({ id, name }) =>
        this.tagService.renameTag(id, name).pipe(
          map((item: TagListItem) => tagsActions.renameSuccess({ item })),
          catchError((error: HttpErrorResponse) =>
            of(tagsActions.renameFailure({ error: error.message }))
          ),
        )
      ),
    )
  );

  readonly merge$ = createEffect(() =>
    this.actions$.pipe(
      ofType(tagsActions.merge),
      mergeMap(({ from_ids, into_id }) =>
        this.tagService.mergeTags({ from_ids, into_id }).pipe(
          map(() => tagsActions.mergeSuccess()),
          catchError((error: HttpErrorResponse) =>
            of(tagsActions.mergeFailure({ error: error.message }))
          ),
        )
      ),
    )
  );

  readonly reloadAfterMerge$ = createEffect(() =>
    this.actions$.pipe(
      ofType(tagsActions.mergeSuccess),
      map(() => tagsActions.load()),
    )
  );

  readonly setAliases$ = createEffect(() =>
    this.actions$.pipe(
      ofType(tagsActions.setAliases),
      mergeMap(({ id, names }) =>
        this.tagService.setTagAliases(id, names).pipe(
          map(() => tagsActions.setAliasesSuccess()),
          catchError((error: HttpErrorResponse) =>
            of(tagsActions.setAliasesFailure({ error: error.message }))
          ),
        )
      ),
    )
  );

  readonly reloadAfterSetAliases$ = createEffect(() =>
    this.actions$.pipe(
      ofType(tagsActions.setAliasesSuccess),
      map(() => tagsActions.load()),
    )
  );

  readonly bulkTag$ = createEffect(() =>
    this.actions$.pipe(
      ofType(tagsActions.bulkTag),
      mergeMap(({ asset_ids, add, remove }) =>
        this.tagService.bulkTag({ asset_ids, add, remove }).pipe(
          map(() => tagsActions.bulkTagSuccess()),
          catchError((error: HttpErrorResponse) =>
            of(tagsActions.bulkTagFailure({ error: error.message }))
          ),
        )
      ),
    )
  );
}
