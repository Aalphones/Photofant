import { Injectable, inject } from '@angular/core';
import { Actions, createEffect, ofType } from '@ngrx/effects';
import { catchError, map, mergeMap, of, switchMap } from 'rxjs';
import type { HttpErrorResponse } from '@angular/common/http';
import type { ClassificationCategory, ClassificationLabel } from '@photofant/models';
import { ClassificationService } from '@photofant/services';
import { classificationActions } from './classification.actions';

@Injectable()
export class ClassificationEffects {
  private readonly actions$ = inject(Actions);
  private readonly classificationService = inject(ClassificationService);

  readonly load$ = createEffect(() =>
    this.actions$.pipe(
      ofType(classificationActions.load),
      switchMap(() =>
        this.classificationService.listCategories().pipe(
          map((categories: ClassificationCategory[]) => classificationActions.loadSuccess({ categories })),
          catchError((error: HttpErrorResponse) =>
            of(classificationActions.loadFailure({ error: error.message }))
          ),
        )
      ),
    )
  );

  readonly createCategory$ = createEffect(() =>
    this.actions$.pipe(
      ofType(classificationActions.createCategory),
      mergeMap(({ name, mode }) =>
        this.classificationService.createCategory({ name, mode }).pipe(
          map((category: ClassificationCategory) => classificationActions.createCategorySuccess({ category })),
          catchError((error: HttpErrorResponse) =>
            of(classificationActions.createCategoryFailure({ error: error.message }))
          ),
        )
      ),
    )
  );

  readonly patchCategory$ = createEffect(() =>
    this.actions$.pipe(
      ofType(classificationActions.patchCategory),
      mergeMap(({ id, patch }) =>
        this.classificationService.patchCategory(id, patch).pipe(
          map((category: ClassificationCategory) => classificationActions.patchCategorySuccess({ category })),
          catchError((error: HttpErrorResponse) =>
            of(classificationActions.patchCategoryFailure({ error: error.message }))
          ),
        )
      ),
    )
  );

  readonly deleteCategory$ = createEffect(() =>
    this.actions$.pipe(
      ofType(classificationActions.deleteCategory),
      mergeMap(({ id }) =>
        this.classificationService.deleteCategory(id).pipe(
          map(() => classificationActions.deleteCategorySuccess({ id })),
          catchError((error: HttpErrorResponse) =>
            of(classificationActions.deleteCategoryFailure({ error: error.message }))
          ),
        )
      ),
    )
  );

  readonly createLabel$ = createEffect(() =>
    this.actions$.pipe(
      ofType(classificationActions.createLabel),
      mergeMap(({ categoryId, name }) =>
        this.classificationService.createLabel(categoryId, { name }).pipe(
          map((label: ClassificationLabel) => classificationActions.createLabelSuccess({ label })),
          catchError((error: HttpErrorResponse) =>
            of(classificationActions.createLabelFailure({ error: error.message }))
          ),
        )
      ),
    )
  );

  readonly patchLabel$ = createEffect(() =>
    this.actions$.pipe(
      ofType(classificationActions.patchLabel),
      mergeMap(({ id, patch }) =>
        this.classificationService.patchLabel(id, patch).pipe(
          map((label: ClassificationLabel) => classificationActions.patchLabelSuccess({ label })),
          catchError((error: HttpErrorResponse) =>
            of(classificationActions.patchLabelFailure({ error: error.message }))
          ),
        )
      ),
    )
  );

  readonly deleteLabel$ = createEffect(() =>
    this.actions$.pipe(
      ofType(classificationActions.deleteLabel),
      mergeMap(({ id, categoryId }) =>
        this.classificationService.deleteLabel(id).pipe(
          map(() => classificationActions.deleteLabelSuccess({ id, categoryId })),
          catchError((error: HttpErrorResponse) =>
            of(classificationActions.deleteLabelFailure({ error: error.message }))
          ),
        )
      ),
    )
  );

  readonly reclassifyAll$ = createEffect(() =>
    this.actions$.pipe(
      ofType(classificationActions.reclassifyAll),
      mergeMap(() =>
        this.classificationService.reclassifyAll().pipe(
          map(({ job_id }: { job_id: string }) => classificationActions.reclassifyAllSuccess({ jobId: job_id })),
          catchError((error: HttpErrorResponse) =>
            of(classificationActions.reclassifyAllFailure({ error: error.message }))
          ),
        )
      ),
    )
  );
}
