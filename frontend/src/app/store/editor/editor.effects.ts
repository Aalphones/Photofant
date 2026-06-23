import { Injectable, inject } from '@angular/core';
import { Actions, createEffect, ofType } from '@ngrx/effects';
import { Store } from '@ngrx/store';
import { concatLatestFrom } from '@ngrx/operators';
import { catchError, EMPTY, map, of, switchMap, concatMap } from 'rxjs';
import type { HttpErrorResponse } from '@angular/common/http';
import type { ApplyStepResponse, CreateSessionResponse, EditorStep, RollbackResponse } from '@photofant/models';
import { EditSessionService, GenerativeService } from '@photofant/services';
import type { FluxEditRequest, InpaintRequest } from '@photofant/services';
import { editorActions } from './editor.actions';
import { editorSelectors } from './editor.selectors';

@Injectable()
export class EditorEffects {
  private readonly actions$ = inject(Actions);
  private readonly store = inject(Store);
  private readonly editSessionService = inject(EditSessionService);
  private readonly generativeService = inject(GenerativeService);

  readonly onInit$ = createEffect(() =>
    this.actions$.pipe(
      ofType(editorActions.init),
      switchMap(({ kind, id }) =>
        this.editSessionService.createSession(kind, id).pipe(
          map((response: CreateSessionResponse) =>
            editorActions.initSuccess({
              sessionKey: response.session_key,
              originalPreviewUrl: response.original_preview_url,
              existingSteps: [],
            })
          ),
          catchError((error: HttpErrorResponse) =>
            of(editorActions.initFailure({ error: error.message }))
          ),
        )
      ),
    )
  );

  readonly onApplyStep$ = createEffect(() =>
    this.actions$.pipe(
      ofType(editorActions.applyStep),
      concatLatestFrom(() => this.store.select(editorSelectors.selectSessionKey)),
      concatMap(([{ op, params, label }, sessionKey]) => {
        if (sessionKey == null) { return EMPTY; }
        return this.editSessionService.applyStep(sessionKey, op, params).pipe(
          map((response: ApplyStepResponse): EditorStep => ({
            seq: response.seq,
            op,
            params,
            label,
            previewUrl: response.preview_url,
          })),
          map((step: EditorStep) => editorActions.applyStepSuccess({ step })),
          catchError((error: HttpErrorResponse) =>
            of(editorActions.applyStepFailure({ error: error.message }))
          ),
        );
      }),
    )
  );

  readonly onRollback$ = createEffect(() =>
    this.actions$.pipe(
      ofType(editorActions.rollback),
      concatLatestFrom(() => this.store.select(editorSelectors.selectSessionKey)),
      concatMap(([{ toSeq }, sessionKey]) => {
        if (sessionKey == null) { return EMPTY; }
        return this.editSessionService.rollback(sessionKey, toSeq).pipe(
          map((response: RollbackResponse) => editorActions.rollbackSuccess({ seq: response.seq })),
          catchError(() => of(editorActions.rollbackSuccess({ seq: toSeq }))),
        );
      }),
    )
  );

  readonly onFluxEdit$ = createEffect(() =>
    this.actions$.pipe(
      ofType(editorActions.fluxEdit),
      concatLatestFrom(() => this.store.select(editorSelectors.selectTargetId)),
      concatMap(([{ prompt, templateId, params }, targetId]) => {
        if (targetId == null) { return EMPTY; }
        const request: FluxEditRequest = {
          prompt,
          template_id: templateId,
          params,
        };
        return this.generativeService.fluxEdit(targetId, request).pipe(
          map((response: { job_id: string }) => editorActions.fluxEditSuccess({ jobId: response.job_id })),
          catchError((error: HttpErrorResponse) =>
            of(editorActions.fluxEditFailure({ error: error.message }))
          ),
        );
      }),
    )
  );

  readonly onInpaint$ = createEffect(() =>
    this.actions$.pipe(
      ofType(editorActions.inpaint),
      concatLatestFrom(() => this.store.select(editorSelectors.selectTargetId)),
      concatMap(([{ mask, prompt, params }, targetId]) => {
        if (targetId == null) { return EMPTY; }
        const request: InpaintRequest = { mask, prompt, params };
        return this.generativeService.inpaint(targetId, request).pipe(
          map((response: { job_id: string }) => editorActions.inpaintSuccess({ jobId: response.job_id })),
          catchError((error: HttpErrorResponse) =>
            of(editorActions.inpaintFailure({ error: error.message }))
          ),
        );
      }),
    )
  );
}
