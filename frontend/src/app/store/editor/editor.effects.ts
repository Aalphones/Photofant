import { Injectable, inject } from '@angular/core';
import { Actions, createEffect, ofType } from '@ngrx/effects';
import { Store } from '@ngrx/store';
import { concatLatestFrom } from '@ngrx/operators';
import { catchError, EMPTY, map, of, switchMap, concatMap } from 'rxjs';
import type { HttpErrorResponse } from '@angular/common/http';
import type { ApplyStepResponse, CreateSessionResponse, EditorStep, RollbackResponse } from '@photofant/models';
import { ComfyUIService, EditSessionService } from '@photofant/services';
import { editorActions } from './editor.actions';
import { editorSelectors } from './editor.selectors';

@Injectable()
export class EditorEffects {
  private readonly actions$ = inject(Actions);
  private readonly store = inject(Store);
  private readonly editSessionService = inject(EditSessionService);
  private readonly comfyuiService = inject(ComfyUIService);

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

  readonly onRunGenerative$ = createEffect(() =>
    this.actions$.pipe(
      ofType(editorActions.runGenerative),
      concatLatestFrom(() => this.store.select(editorSelectors.selectTargetId)),
      concatMap(([{ task, imageSlotKey, prompt, resolution, maskDataUrl }, targetId]) => {
        if (targetId == null) { return EMPTY; }
        // Editor-Asset an den Bild-Slot binden. Bei Inpaint trägt zusätzlich die Maske
        // dieselbe asset_id — das Backend injiziert sie in den Masken-Slot.
        const mask = maskDataUrl != null
          ? { asset_id: targetId, mask_data_url: maskDataUrl }
          : null;
        return this.comfyuiService.runDefaultWorkflow(task, {
          target_asset_ids: [targetId],
          inputs: { [imageSlotKey]: targetId },
          prompt,
          resolution,
          mask,
        }).pipe(
          map((response: { jobs: { job_id: string }[] }) =>
            editorActions.runGenerativeSuccess({ jobId: response.jobs[0]?.job_id ?? '' })
          ),
          catchError((error: HttpErrorResponse) =>
            of(editorActions.runGenerativeFailure({ error: error.message }))
          ),
        );
      }),
    )
  );
}
