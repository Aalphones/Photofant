import { Injectable, inject } from '@angular/core';
import { Actions, createEffect, ofType } from '@ngrx/effects';
import { Store } from '@ngrx/store';
import { concatLatestFrom } from '@ngrx/operators';
import { catchError, filter, map, mergeMap, of, switchMap } from 'rxjs';
import type { HttpErrorResponse } from '@angular/common/http';
import type { Collection, CollectionDetail, Job } from '@photofant/models';
import { CollectionService } from '@photofant/services';
import { jobsActions } from '../jobs/jobs.actions';
import { collectionsActions } from './collections.actions';
import { collectionsFeature } from './collections.reducer';

@Injectable()
export class CollectionsEffects {
  private readonly actions$ = inject(Actions);
  private readonly store = inject(Store);
  private readonly collectionService = inject(CollectionService);

  readonly load$ = createEffect(() =>
    this.actions$.pipe(
      ofType(collectionsActions.load),
      switchMap(() =>
        this.collectionService.listCollections().pipe(
          map((items: Collection[]) => collectionsActions.loadSuccess({ items })),
          catchError((error: HttpErrorResponse) =>
            of(collectionsActions.loadFailure({ error: error.message }))
          ),
        )
      ),
    )
  );

  readonly loadDetail$ = createEffect(() =>
    this.actions$.pipe(
      ofType(collectionsActions.loadDetail),
      switchMap(({ id }) =>
        this.collectionService.getCollection(id).pipe(
          map((detail: CollectionDetail) => collectionsActions.loadDetailSuccess({ detail })),
          catchError((error: HttpErrorResponse) =>
            of(collectionsActions.loadDetailFailure({ error: error.message }))
          ),
        )
      ),
    )
  );

  readonly create$ = createEffect(() =>
    this.actions$.pipe(
      ofType(collectionsActions.create),
      mergeMap(({ request }) =>
        this.collectionService.createCollection(request).pipe(
          map((detail: CollectionDetail) => collectionsActions.createSuccess({ detail })),
          catchError((error: HttpErrorResponse) =>
            of(collectionsActions.createFailure({ error: error.message }))
          ),
        )
      ),
    )
  );

  readonly update$ = createEffect(() =>
    this.actions$.pipe(
      ofType(collectionsActions.update),
      mergeMap(({ id, request }) =>
        this.collectionService.updateCollection(id, request).pipe(
          map((detail: CollectionDetail) => collectionsActions.updateSuccess({ detail })),
          catchError((error: HttpErrorResponse) =>
            of(collectionsActions.updateFailure({ error: error.message }))
          ),
        )
      ),
    )
  );

  readonly delete$ = createEffect(() =>
    this.actions$.pipe(
      ofType(collectionsActions.delete),
      mergeMap(({ id }) =>
        this.collectionService.deleteCollection(id).pipe(
          map(() => collectionsActions.deleteSuccess({ id })),
          catchError((error: HttpErrorResponse) =>
            of(collectionsActions.deleteFailure({ error: error.message }))
          ),
        )
      ),
    )
  );

  readonly addTrigger$ = createEffect(() =>
    this.actions$.pipe(
      ofType(collectionsActions.addTrigger),
      mergeMap(({ collectionId, request }) =>
        this.collectionService.addTrigger(collectionId, request).pipe(
          map(() => collectionsActions.addTriggerSuccess({ collectionId })),
          catchError((error: HttpErrorResponse) =>
            of(collectionsActions.addTriggerFailure({ error: error.message }))
          ),
        )
      ),
    )
  );

  readonly deleteTrigger$ = createEffect(() =>
    this.actions$.pipe(
      ofType(collectionsActions.deleteTrigger),
      mergeMap(({ collectionId, triggerId }) =>
        this.collectionService.deleteTrigger(collectionId, triggerId).pipe(
          map(() => collectionsActions.deleteTriggerSuccess({ collectionId })),
          catchError((error: HttpErrorResponse) =>
            of(collectionsActions.deleteTriggerFailure({ error: error.message }))
          ),
        )
      ),
    )
  );

  readonly updateTrigger$ = createEffect(() =>
    this.actions$.pipe(
      ofType(collectionsActions.updateTrigger),
      mergeMap(({ collectionId, triggerId, negate }) =>
        this.collectionService.updateTrigger(collectionId, triggerId, negate).pipe(
          map(() => collectionsActions.updateTriggerSuccess({ collectionId })),
          catchError((error: HttpErrorResponse) =>
            of(collectionsActions.updateTriggerFailure({ error: error.message }))
          ),
        )
      ),
    )
  );

  // Trigger change → reload that album's detail (triggers list) right away.
  readonly reloadDetailAfterTrigger$ = createEffect(() =>
    this.actions$.pipe(
      ofType(
        collectionsActions.addTriggerSuccess,
        collectionsActions.deleteTriggerSuccess,
        collectionsActions.updateTriggerSuccess,
      ),
      map(({ collectionId }) => collectionsActions.loadDetail({ id: collectionId })),
    )
  );

  readonly addItems$ = createEffect(() =>
    this.actions$.pipe(
      ofType(collectionsActions.addItems),
      mergeMap(({ collectionId, assetIds }) =>
        this.collectionService.addItems(collectionId, assetIds).pipe(
          map(() => collectionsActions.addItemsSuccess()),
          catchError((error: HttpErrorResponse) =>
            of(collectionsActions.addItemsFailure({ error: error.message }))
          ),
        )
      ),
    )
  );

  readonly reorder$ = createEffect(() =>
    this.actions$.pipe(
      ofType(collectionsActions.reorder),
      mergeMap(({ collectionId, assetIds }) =>
        this.collectionService.setOrder(collectionId, assetIds).pipe(
          map(() => collectionsActions.reorderSuccess({ collectionId })),
          catchError((error: HttpErrorResponse) =>
            of(collectionsActions.reorderFailure({ error: error.message }))
          ),
        )
      ),
    )
  );

  // Reorder changes item_order → refresh the open detail right away.
  readonly reloadDetailAfterReorder$ = createEffect(() =>
    this.actions$.pipe(
      ofType(collectionsActions.reorderSuccess),
      map(({ collectionId }) => collectionsActions.loadDetail({ id: collectionId })),
    )
  );

  // Member counts change asynchronously (re-evaluation runs in the queue). When such a
  // job finishes, refresh the list and the open detail so counts and membership are current.
  readonly reloadAfterReevaluate$ = createEffect(() =>
    this.actions$.pipe(
      ofType(jobsActions.upsertJob),
      filter(({ job }: { job: Job }) => job.kind === 'reevaluate' && job.state === 'done'),
      concatLatestFrom(() => this.store.select(collectionsFeature.selectDetail)),
      mergeMap(([, detail]) =>
        detail
          ? of(collectionsActions.load(), collectionsActions.loadDetail({ id: detail.id }))
          : of(collectionsActions.load())
      ),
    )
  );

  // List counts also shift after manual item adds.
  readonly reloadAfterItemAdd$ = createEffect(() =>
    this.actions$.pipe(
      ofType(collectionsActions.addItemsSuccess),
      map(() => collectionsActions.load()),
    )
  );
}
