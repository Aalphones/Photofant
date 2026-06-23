import { Injectable, inject } from '@angular/core';
import { Actions, createEffect, ofType } from '@ngrx/effects';
import { catchError, map, of, switchMap } from 'rxjs';
import type { HttpErrorResponse } from '@angular/common/http';
import type { PromptTemplateDto } from '@photofant/models';
import { PromptTemplateService } from '@photofant/services';
import { promptTemplateActions } from './prompt-templates.actions';

@Injectable()
export class PromptTemplateEffects {
  private readonly actions$ = inject(Actions);
  private readonly service = inject(PromptTemplateService);

  readonly onLoad$ = createEffect(() =>
    this.actions$.pipe(
      ofType(promptTemplateActions.load),
      switchMap(() =>
        this.service.list().pipe(
          map((templates: PromptTemplateDto[]) => promptTemplateActions.loadSuccess({ templates })),
          catchError((error: HttpErrorResponse) =>
            of(promptTemplateActions.loadFailure({ error: error.message }))
          ),
        )
      ),
    )
  );

  readonly onCreate$ = createEffect(() =>
    this.actions$.pipe(
      ofType(promptTemplateActions.create),
      switchMap(({ request }) =>
        this.service.create(request).pipe(
          map((template: PromptTemplateDto) => promptTemplateActions.createSuccess({ template })),
          catchError((error: HttpErrorResponse) =>
            of(promptTemplateActions.createFailure({ error: error.message }))
          ),
        )
      ),
    )
  );

  readonly onUpdate$ = createEffect(() =>
    this.actions$.pipe(
      ofType(promptTemplateActions.update),
      switchMap(({ id, request }) =>
        this.service.update(id, request).pipe(
          map((template: PromptTemplateDto) => promptTemplateActions.updateSuccess({ template })),
          catchError((error: HttpErrorResponse) =>
            of(promptTemplateActions.updateFailure({ error: error.message }))
          ),
        )
      ),
    )
  );

  readonly onDelete$ = createEffect(() =>
    this.actions$.pipe(
      ofType(promptTemplateActions.delete),
      switchMap(({ id }) =>
        this.service.delete(id).pipe(
          map(() => promptTemplateActions.deleteSuccess({ id })),
          catchError((error: HttpErrorResponse) =>
            of(promptTemplateActions.deleteFailure({ error: error.message }))
          ),
        )
      ),
    )
  );
}
