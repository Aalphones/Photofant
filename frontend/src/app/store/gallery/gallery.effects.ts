import { Injectable, inject } from '@angular/core';
import { Actions, createEffect, ofType } from '@ngrx/effects';
import { Store } from '@ngrx/store';
import { concatLatestFrom } from '@ngrx/operators';
import { catchError, EMPTY, filter, map, mergeMap, of, switchMap } from 'rxjs';
import type { HttpErrorResponse } from '@angular/common/http';
import type { AssetDto, AssetsPage, Job } from '@photofant/models';
import { AssetService } from '@photofant/services';
import { filtersActions } from '../filters/filters.actions';
import { jobsActions } from '../jobs/jobs.actions';
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
        filtersActions.setSources,
        filtersActions.setQualityMin,
        filtersActions.setTagIds,
        filtersActions.clearAllFilters,
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
          sources: params.sources,
          qualityMin: params.qualityMin,
          tagIds: params.tagIds,
        }).pipe(
          map((result: AssetsPage) => galleryActions.loadPageSuccess({
            items: result.items,
            total: result.total,
            page: result.page,
            pageSize: result.page_size,
            facets: result.facets,
          })),
          catchError((error: HttpErrorResponse) =>
            of(galleryActions.loadPageFailure({ error: error.message }))
          ),
        )
      ),
    )
  );

  readonly reloadAfterImport$ = createEffect(() =>
    this.actions$.pipe(
      ofType(jobsActions.upsertJob),
      filter(({ job }: { job: Job }) =>
        (job.kind === 'import' || job.kind === 'scan') && job.state === 'done'
      ),
      map(() => galleryActions.reset()),
    )
  );

  readonly onLightboxNext$ = createEffect(() =>
    this.actions$.pipe(
      ofType(galleryActions.lightboxNext),
      concatLatestFrom(() => this.store.select(gallerySelectors.selectLightboxNavContext)),
      mergeMap(([, { assets, lightboxId, hasMore, isLoading }]) => {
        const index = lightboxId != null ? assets.findIndex((asset) => asset.id === lightboxId) : -1;
        if (index < 0) return EMPTY;
        if (index < assets.length - 1) {
          return of(galleryActions.lightboxGoTo({ id: assets[index + 1]!.id })); // index < length - 1 guarantees slot exists
        }
        if (hasMore && !isLoading) {
          return of(galleryActions.lightboxMarkPendingNext(), galleryActions.requestNextPage());
        }
        return EMPTY;
      }),
    )
  );

  readonly onLightboxPrev$ = createEffect(() =>
    this.actions$.pipe(
      ofType(galleryActions.lightboxPrev),
      concatLatestFrom(() => this.store.select(gallerySelectors.selectLightboxNavContext)),
      mergeMap(([, { assets, lightboxId }]) => {
        const index = lightboxId != null ? assets.findIndex((asset) => asset.id === lightboxId) : -1;
        if (index > 0) {
          return of(galleryActions.lightboxGoTo({ id: assets[index - 1]!.id })); // index > 0 guarantees slot exists
        }
        return EMPTY;
      }),
    )
  );

  readonly toggleFavourite$ = createEffect(() =>
    this.actions$.pipe(
      ofType(galleryActions.toggleFavourite),
      mergeMap(({ id, value }) =>
        this.assetService.setFavourite(id, value).pipe(
          map((asset: AssetDto) => galleryActions.toggleFavouriteSuccess({ asset })),
          catchError(() => of(galleryActions.toggleFavouriteFailure({ id, previous: !value }))),
        )
      ),
    )
  );

  readonly deleteAsset$ = createEffect(() =>
    this.actions$.pipe(
      ofType(galleryActions.deleteAsset),
      mergeMap(({ id }) =>
        this.assetService.deleteAsset(id).pipe(
          map(() => galleryActions.deleteAssetSuccess({ id })),
          catchError((error: HttpErrorResponse) =>
            of(galleryActions.deleteAssetFailure({ error: error.message }))
          ),
        )
      ),
    )
  );
}
