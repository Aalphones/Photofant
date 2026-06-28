import { Injectable, inject } from '@angular/core';
import { Actions, createEffect, ofType } from '@ngrx/effects';
import { catchError, map, of, switchMap } from 'rxjs';
import type { HttpErrorResponse } from '@angular/common/http';
import { ComfyUIService } from '@photofant/services';
import { comfyuiActions } from './comfyui.actions';

@Injectable()
export class ComfyUIEffects {
  private readonly actions$ = inject(Actions);
  private readonly comfyuiService = inject(ComfyUIService);

  readonly loadConfig$ = createEffect(() =>
    this.actions$.pipe(
      ofType(comfyuiActions.loadConfig),
      switchMap(() =>
        this.comfyuiService.loadConfig().pipe(
          map((config) => comfyuiActions.loadConfigSuccess({ config })),
          catchError((error: HttpErrorResponse) =>
            of(comfyuiActions.loadConfigFailure({ error: error.message }))
          ),
        )
      ),
    )
  );

  readonly saveConfig$ = createEffect(() =>
    this.actions$.pipe(
      ofType(comfyuiActions.saveConfig),
      switchMap(({ config }) =>
        this.comfyuiService.saveConfig(config).pipe(
          map((saved) => comfyuiActions.saveConfigSuccess({ config: saved })),
          catchError((error: HttpErrorResponse) =>
            of(comfyuiActions.saveConfigFailure({ error: error.message }))
          ),
        )
      ),
    )
  );

  readonly testConnection$ = createEffect(() =>
    this.actions$.pipe(
      ofType(comfyuiActions.testConnection),
      switchMap(() =>
        this.comfyuiService.testConnection().pipe(
          map(({ ok, detail }) => comfyuiActions.testConnectionSuccess({ ok, detail })),
          catchError((error: HttpErrorResponse) =>
            of(comfyuiActions.testConnectionFailure({ error: error.message }))
          ),
        )
      ),
    )
  );

  readonly loadWorkflows$ = createEffect(() =>
    this.actions$.pipe(
      ofType(comfyuiActions.loadWorkflows),
      switchMap(() =>
        this.comfyuiService.listWorkflows().pipe(
          map((workflows) => comfyuiActions.loadWorkflowsSuccess({ workflows })),
          catchError((error: HttpErrorResponse) =>
            of(comfyuiActions.loadWorkflowsFailure({ error: error.message }))
          ),
        )
      ),
    )
  );

  readonly createWorkflow$ = createEffect(() =>
    this.actions$.pipe(
      ofType(comfyuiActions.createWorkflow),
      switchMap(({ file, name, category }) =>
        this.comfyuiService.createWorkflow(file, name, category).pipe(
          map((workflow) => comfyuiActions.createWorkflowSuccess({ workflow })),
          catchError((error: HttpErrorResponse) =>
            of(comfyuiActions.createWorkflowFailure({ error: extractErrorMessage(error) }))
          ),
        )
      ),
    )
  );

  readonly updateWorkflow$ = createEffect(() =>
    this.actions$.pipe(
      ofType(comfyuiActions.updateWorkflow),
      switchMap(({ workflowId, patch }) =>
        this.comfyuiService.updateWorkflow(workflowId, patch).pipe(
          map((workflow) => comfyuiActions.updateWorkflowSuccess({ workflow })),
          catchError((error: HttpErrorResponse) =>
            of(comfyuiActions.updateWorkflowFailure({ error: extractErrorMessage(error) }))
          ),
        )
      ),
    )
  );

  readonly deleteWorkflow$ = createEffect(() =>
    this.actions$.pipe(
      ofType(comfyuiActions.deleteWorkflow),
      switchMap(({ workflowId }) =>
        this.comfyuiService.deleteWorkflow(workflowId).pipe(
          map(() => comfyuiActions.deleteWorkflowSuccess({ workflowId })),
          catchError((error: HttpErrorResponse) =>
            of(comfyuiActions.deleteWorkflowFailure({ error: error.message }))
          ),
        )
      ),
    )
  );

  readonly activateWorkflow$ = createEffect(() =>
    this.actions$.pipe(
      ofType(comfyuiActions.activateWorkflow),
      switchMap(({ workflowId }) =>
        this.comfyuiService.activateWorkflow(workflowId).pipe(
          map((workflow) => comfyuiActions.activateWorkflowSuccess({ workflow })),
          catchError((error: HttpErrorResponse) =>
            of(comfyuiActions.activateWorkflowFailure({ error: extractErrorMessage(error) }))
          ),
        )
      ),
    )
  );

  readonly deactivateWorkflow$ = createEffect(() =>
    this.actions$.pipe(
      ofType(comfyuiActions.deactivateWorkflow),
      switchMap(({ workflowId }) =>
        this.comfyuiService.deactivateWorkflow(workflowId).pipe(
          map((workflow) => comfyuiActions.deactivateWorkflowSuccess({ workflow })),
          catchError((error: HttpErrorResponse) =>
            of(comfyuiActions.deactivateWorkflowFailure({ error: error.message }))
          ),
        )
      ),
    )
  );

  readonly duplicateWorkflow$ = createEffect(() =>
    this.actions$.pipe(
      ofType(comfyuiActions.duplicateWorkflow),
      switchMap(({ workflowId }) =>
        this.comfyuiService.duplicateWorkflow(workflowId).pipe(
          map((workflow) => comfyuiActions.duplicateWorkflowSuccess({ workflow })),
          catchError((error: HttpErrorResponse) =>
            of(comfyuiActions.duplicateWorkflowFailure({ error: error.message }))
          ),
        )
      ),
    )
  );

  readonly redetectInputs$ = createEffect(() =>
    this.actions$.pipe(
      ofType(comfyuiActions.redetectInputs),
      switchMap(({ workflowId }) =>
        this.comfyuiService.redetectInputs(workflowId).pipe(
          map((workflow) => comfyuiActions.redetectInputsSuccess({ workflow })),
          catchError((error: HttpErrorResponse) =>
            of(comfyuiActions.redetectInputsFailure({ error: extractErrorMessage(error) }))
          ),
        )
      ),
    )
  );
}

function extractErrorMessage(error: HttpErrorResponse): string {
  if (error.error && typeof error.error === 'object' && 'detail' in error.error) {
    const detail = error.error.detail;
    if (typeof detail === 'string') {
      return detail;
    }
    if (typeof detail === 'object' && detail !== null && 'message' in detail) {
      return String(detail.message);
    }
  }
  return error.message;
}
