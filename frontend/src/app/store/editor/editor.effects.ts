import { Injectable, inject } from '@angular/core';
import { Actions, createEffect, ofType } from '@ngrx/effects';
import { Store } from '@ngrx/store';
import { concatLatestFrom } from '@ngrx/operators';
import { catchError, EMPTY, filter, map, of, switchMap, concatMap, take } from 'rxjs';
import type { HttpErrorResponse } from '@angular/common/http';
import type { ApplyStepResponse, AssetDetailDto, CreateSessionResponse, EditorStep, Job, RollbackResponse, VersionDto } from '@photofant/models';
import { AssetService, ComfyUIService, EditSessionService, JobsService } from '@photofant/services';
import { editorActions } from './editor.actions';
import { editorSelectors } from './editor.selectors';

@Injectable()
export class EditorEffects {
  private readonly actions$ = inject(Actions);
  private readonly store = inject(Store);
  private readonly editSessionService = inject(EditSessionService);
  private readonly comfyuiService = inject(ComfyUIService);
  private readonly jobsService = inject(JobsService);
  private readonly assetService = inject(AssetService);

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

  readonly onSave$ = createEffect(() =>
    this.actions$.pipe(
      ofType(editorActions.save),
      concatLatestFrom(() => this.store.select(editorSelectors.selectSessionKey)),
      concatMap(([{ mode }, sessionKey]) => {
        if (sessionKey == null) { return EMPTY; }
        return this.editSessionService.save(sessionKey, mode).pipe(
          map((version: VersionDto) => editorActions.saveSuccess({ version })),
          catchError((error: HttpErrorResponse) =>
            of(editorActions.saveFailure({ error: error.message }))
          ),
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

  // SSE-Polling: wartet bis der ComfyUI-Job DONE/ERROR ist, dann holt die neue Version
  readonly onRunGenerativePoll$ = createEffect(() =>
    this.actions$.pipe(
      ofType(editorActions.runGenerativeSuccess),
      concatLatestFrom(() => this.store.select(editorSelectors.selectTargetId)),
      switchMap(([{ jobId }, targetId]) => {
        if (!jobId || targetId == null) { return EMPTY; }
        return this.jobsService.streamJobs().pipe(
          filter((job: Job) => job.id === jobId && (job.state === 'done' || job.state === 'error')),
          take(1),
          switchMap((job: Job) => {
            if (job.state === 'error') {
              return of(editorActions.runGenerativeFailure({
                error: job.error ?? 'Generierung in ComfyUI fehlgeschlagen',
              }));
            }
            return this.assetService.getAsset(targetId).pipe(
              map((asset: AssetDetailDto) => {
                const versions = asset.versions ?? [];
                const newest = versions
                  .filter((version: VersionDto) => version.params?.['source'] === 'comfyui_auto_import')
                  .sort((versionA: VersionDto, versionB: VersionDto) => {
                    const timeA = versionA.created_at ? new Date(versionA.created_at).getTime() : 0;
                    const timeB = versionB.created_at ? new Date(versionB.created_at).getTime() : 0;
                    return timeB - timeA;
                  })[0];
                if (!newest) {
                  return editorActions.runGenerativeFailure({
                    error: 'Importiertes Ergebnis nicht in den Versionen gefunden',
                  });
                }
                return editorActions.runGenerativeDone({
                  versionId: newest.id,
                  previewUrl: `/api/versions/${newest.id}/file`,
                  thumbnailUrl: newest.thumbnail_url,
                });
              }),
              catchError((error: HttpErrorResponse) =>
                of(editorActions.runGenerativeFailure({ error: error.message }))
              ),
            );
          }),
          catchError((error: Error) =>
            of(editorActions.runGenerativeFailure({ error: error.message }))
          ),
        );
      }),
    )
  );
}
