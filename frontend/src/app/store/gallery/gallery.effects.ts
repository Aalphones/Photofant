import { Injectable, inject } from '@angular/core';
import { Actions, createEffect, ofType, ROOT_EFFECTS_INIT } from '@ngrx/effects';
import { Store } from '@ngrx/store';
import { concatLatestFrom } from '@ngrx/operators';
import { catchError, EMPTY, filter, map, merge, mergeMap, of, switchMap, tap } from 'rxjs';
import type { Action } from '@ngrx/store';
import type { HttpErrorResponse } from '@angular/common/http';
import type { AssetDetailDto, AssetDto, AssetsPage, FacesPage, Job } from '@photofant/models';
import { AssetService, PersonService, SettingsService } from '@photofant/services';
import { filtersActions } from '../filters/filters.actions';
import { searchActions } from '../search/search.actions';
import { jobsActions } from '../jobs/jobs.actions';
import { galleryActions } from './gallery.actions';
import { gallerySelectors } from './gallery.selectors';

@Injectable()
export class GalleryEffects {
  private readonly actions$ = inject(Actions);
  private readonly store = inject(Store);
  private readonly assetService = inject(AssetService);
  private readonly personService = inject(PersonService);
  private readonly settingsService = inject(SettingsService);

  readonly initDensity$ = createEffect(() =>
    this.actions$.pipe(
      ofType(ROOT_EFFECTS_INIT),
      map(() => filtersActions.setDensity({ density: this.settingsService.density() })),
    )
  );

  readonly saveDensity$ = createEffect(() =>
    this.actions$.pipe(
      ofType(filtersActions.setDensity),
      tap(({ density }) => { this.settingsService.setDensity(density); }),
    ),
    { dispatch: false }
  );

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
        filtersActions.setCollectionId,
        filtersActions.setPersonId,
        filtersActions.setFramings,
        filtersActions.setMediaType,
        filtersActions.clearAllFilters,
        searchActions.setQuery,
        searchActions.setMode,
        searchActions.clear,
      ),
      map(() => galleryActions.reset()),
    )
  );

  readonly fetchPage$ = createEffect(() =>
    this.actions$.pipe(
      ofType(galleryActions.requestPage, galleryActions.requestNextPage, galleryActions.reset),
      concatLatestFrom(() => this.store.select(gallerySelectors.selectFetchParams)),
      switchMap(([, params]) => {
        if (params.mediaType === 'faces') {
          const faceParams: { page: number; page_size: number; person_id?: number } = {
            page: params.page,
            page_size: params.pageSize,
          };
          if (params.personId != null) { faceParams.person_id = params.personId; }
          return this.personService.listFacesGallery(faceParams).pipe(
            map((result: FacesPage) => galleryActions.loadFacesPageSuccess({
              items: result.items,
              total: result.total,
              page: result.page,
              pageSize: result.page_size,
            })),
            catchError((error: HttpErrorResponse) =>
              of(galleryActions.loadPageFailure({ error: error.message }))
            ),
          );
        }

        const assetFetch$ = this.assetService.listAssets({
          page: params.page,
          page_size: params.pageSize,
          sort: params.sort,
          order: params.order,
          favourite: params.favourite,
          sources: params.sources,
          qualityMin: params.qualityMin,
          tagIds: params.tagIds,
          collectionId: params.collectionId,
          personId: params.personId,
          framings: params.framings,
          ...(params.q ? { q: params.q, qMode: params.qMode } : {}),
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
        );

        // In 'all' mode, fetch faces for the current asset page after assets are loaded
        if (params.mediaType === 'all') {
          return assetFetch$.pipe(
            mergeMap((assetAction: Action) => {
              if (assetAction.type !== galleryActions.loadPageSuccess.type) {
                return of(assetAction);
              }
              const successAction = assetAction as ReturnType<typeof galleryActions.loadPageSuccess>;
              const assetIds = successAction.items.map((item: AssetDto) => item.id);
              if (assetIds.length === 0) {
                return of(assetAction);
              }
              const faceParams: { page: number; page_size: number; person_id?: number; asset_ids: number[] } = {
                page: successAction.page,
                page_size: 500,
                asset_ids: assetIds,
              };
              if (params.personId != null) { faceParams.person_id = params.personId; }
              const faceFetch$ = this.personService.listFacesGallery(faceParams).pipe(
                map((result: FacesPage) => galleryActions.loadFacesPageSuccess({
                  items: result.items,
                  total: result.total,
                  page: successAction.page,
                  pageSize: result.page_size,
                })),
                catchError(() => EMPTY),
              );
              return merge(of(assetAction), faceFetch$);
            }),
          );
        }

        return assetFetch$;
      }),
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

  readonly openFaceLightbox$ = createEffect(() =>
    this.actions$.pipe(
      ofType(galleryActions.openFaceLightbox),
      mergeMap(({ assetId }) =>
        this.assetService.getAsset(assetId).pipe(
          mergeMap((detail: AssetDetailDto) => [
            galleryActions.injectAsset({ asset: detail }),
            galleryActions.openLightbox({ id: assetId }),
          ]),
          catchError(() => EMPTY),
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
