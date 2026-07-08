import { Injectable, inject } from '@angular/core';
import { Actions, ROOT_EFFECTS_INIT, createEffect, ofType } from '@ngrx/effects';
import { Store } from '@ngrx/store';
import { concatLatestFrom } from '@ngrx/operators';
import { catchError, map, mergeMap, of, switchMap } from 'rxjs';
import type { HttpErrorResponse } from '@angular/common/http';
import { DUPE_PAGE_SIZE } from '@photofant/models';
import type { DupePage, FaceReviewItem } from '@photofant/models';
import { ReviewService } from '@photofant/services';
import { reviewActions } from './review.actions';
import { reviewSelectors } from './review.selectors';

@Injectable()
export class ReviewEffects {
  private readonly actions$ = inject(Actions);
  private readonly store = inject(Store);
  private readonly reviewService = inject(ReviewService);

  readonly init$ = createEffect(() =>
    this.actions$.pipe(
      ofType(ROOT_EFFECTS_INIT),
      map(() => reviewActions.loadDupePairs()),
    ),
  );

  readonly loadDupePairs$ = createEffect(() =>
    this.actions$.pipe(
      ofType(reviewActions.loadDupePairs),
      switchMap(() =>
        this.reviewService.listDupePairs(0, DUPE_PAGE_SIZE).pipe(
          map((page: DupePage) => reviewActions.loadDupePairsSuccess({ pairs: page.items, total: page.total })),
          catchError((error: HttpErrorResponse) =>
            of(reviewActions.loadDupePairsFailure({ error: error.message })),
          ),
        ),
      ),
    ),
  );

  readonly loadMoreDupePairs$ = createEffect(() =>
    this.actions$.pipe(
      ofType(reviewActions.loadMoreDupePairs),
      concatLatestFrom(() => this.store.select(reviewSelectors.selectOffset)),
      switchMap(([, offset]) =>
        this.reviewService.listDupePairs(offset, DUPE_PAGE_SIZE).pipe(
          map((page: DupePage) => reviewActions.loadMoreDupePairsSuccess({ pairs: page.items, total: page.total })),
          catchError((error: HttpErrorResponse) =>
            of(reviewActions.loadMoreDupePairsFailure({ error: error.message })),
          ),
        ),
      ),
    ),
  );

  readonly resolveDupePair$ = createEffect(() =>
    this.actions$.pipe(
      ofType(reviewActions.resolveDupePair),
      switchMap(({ itemId, resolution }) =>
        this.reviewService.resolveDupePair(itemId, resolution).pipe(
          map(() => reviewActions.resolveDupePairSuccess({ itemId })),
          catchError((error: HttpErrorResponse) =>
            of(reviewActions.resolveDupePairFailure({ error: error.message })),
          ),
        ),
      ),
    ),
  );

  readonly clearDupeCandidates$ = createEffect(() =>
    this.actions$.pipe(
      ofType(reviewActions.clearDupeCandidates),
      switchMap(() =>
        this.reviewService.clearDupeCandidates().pipe(
          map((response: { deleted: number }) =>
            reviewActions.clearDupeCandidatesSuccess({ deleted: response.deleted }),
          ),
          catchError((error: HttpErrorResponse) =>
            of(reviewActions.clearDupeCandidatesFailure({ error: error.message })),
          ),
        ),
      ),
    ),
  );

  readonly triggerDupeScan$ = createEffect(() =>
    this.actions$.pipe(
      ofType(reviewActions.triggerDupeScan),
      switchMap(() =>
        this.reviewService.triggerDupeScan('all').pipe(
          map((response: { job_id: string }) =>
            reviewActions.triggerDupeScanSuccess({ jobId: response.job_id }),
          ),
          catchError((error: HttpErrorResponse) =>
            of(reviewActions.triggerDupeScanFailure({ error: error.message })),
          ),
        ),
      ),
    ),
  );

  readonly triggerDupeScanSelection$ = createEffect(() =>
    this.actions$.pipe(
      ofType(reviewActions.triggerDupeScanSelection),
      switchMap(({ assetIds }) =>
        this.reviewService.triggerDupeScan('selection', assetIds).pipe(
          map((response: { job_id: string }) =>
            reviewActions.triggerDupeScanSelectionSuccess({ jobId: response.job_id }),
          ),
          catchError((error: HttpErrorResponse) =>
            of(reviewActions.triggerDupeScanSelectionFailure({ error: error.message })),
          ),
        ),
      ),
    ),
  );

  readonly loadFaceQueue$ = createEffect(() =>
    this.actions$.pipe(
      ofType(reviewActions.loadFaceQueue),
      switchMap(() =>
        this.reviewService.listFaceReviewQueue().pipe(
          map((items: FaceReviewItem[]) => reviewActions.loadFaceQueueSuccess({ items })),
          catchError((error: HttpErrorResponse) =>
            of(reviewActions.loadFaceQueueFailure({ error: error.message })),
          ),
        ),
      ),
    ),
  );

  readonly resolveFaceReview$ = createEffect(() =>
    this.actions$.pipe(
      ofType(reviewActions.resolveFaceReview),
      mergeMap(({ faceId, action, personId }) =>
        this.reviewService.resolveFaceReview(faceId, action, personId).pipe(
          map(() => reviewActions.resolveFaceReviewSuccess({ faceId })),
          catchError((error: HttpErrorResponse) =>
            of(reviewActions.resolveFaceReviewFailure({ error: error.message })),
          ),
        ),
      ),
    ),
  );
}
