import { Injectable, inject } from '@angular/core';
import { Actions, createEffect, ofType } from '@ngrx/effects';
import { catchError, map, of, switchMap } from 'rxjs';
import type { HttpErrorResponse } from '@angular/common/http';
import { McpService } from '@photofant/services';
import { mcpActions } from './mcp.actions';

@Injectable()
export class McpEffects {
  private readonly actions$ = inject(Actions);
  private readonly mcpService = inject(McpService);

  readonly loadConfig$ = createEffect(() =>
    this.actions$.pipe(
      ofType(mcpActions.loadConfig),
      switchMap(() =>
        this.mcpService.loadConfig().pipe(
          map((config) => mcpActions.loadConfigSuccess({ config })),
          catchError((error: HttpErrorResponse) =>
            of(mcpActions.loadConfigFailure({ error: error.message }))
          ),
        )
      ),
    )
  );

  readonly saveConfig$ = createEffect(() =>
    this.actions$.pipe(
      ofType(mcpActions.saveConfig),
      switchMap(({ config }) =>
        this.mcpService.saveConfig(config).pipe(
          map((saved) => mcpActions.saveConfigSuccess({ config: saved })),
          catchError((error: HttpErrorResponse) =>
            of(mcpActions.saveConfigFailure({ error: error.message }))
          ),
        )
      ),
    )
  );
}
