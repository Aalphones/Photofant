import { Injectable, inject } from '@angular/core';
import { Actions, createEffect, ofType } from '@ngrx/effects';
import { Store } from '@ngrx/store';
import { concatLatestFrom } from '@ngrx/operators';
import { catchError, map, of, switchMap } from 'rxjs';
import type { HttpErrorResponse } from '@angular/common/http';
import type { AssetsPage } from '@photofant/models';
import { AssetService } from '@photofant/services';
import { filtersActions } from '../filters/filters.actions';
import { galleryActions } from './gallery.actions';
import { gallerySelectors } from './gallery.selectors';

@Injectable()
export class GalleryEffects {
  private readonly actions$ = inject(Actions);
  private readonly store = inject(Store);
  private readonly assetService = inject(AssetService);

  readonly onFiltersChange$ = createEffect(() =>
    this.actions$.pipe(
      ofType(
        filtersActions.setSort,
        filtersActions.setGroup,
        filtersActions.setDensity,
        filtersActions.setFavourite,
      ),
      map(() => galleryActions.reset()),
    )
  );

  readonly fetchPage$ = createEffect(() =>
    this.actions$.pipe(
      ofType(galleryActions.requestPage, galleryActions.requestNextPage, galleryActions.reset),
      concatLatestFrom(() => this.store.select(gallerySelectors.selectFetchParams)),
      switchMap(([, params]) =>
        this.assetService.listAssets({
          page: params.page,
          page_size: params.pageSize,
          sort: params.sort,
          order: params.order,
          favourite: params.favourite,
        }).pipe(
          map((result: AssetsPage) => galleryActions.loadPageSuccess({
            items: result.items,
            total: result.total,
            page: result.page,
            pageSize: result.page_size,
          })),
          catchError((error: HttpErrorResponse) =>
            of(galleryActions.loadPageFailure({ error: error.message }))
          ),
        )
      ),
    )
  );
}
