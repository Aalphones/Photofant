import { Injectable, inject } from '@angular/core';
import { Actions, createEffect, ofType } from '@ngrx/effects';
import { catchError, map, of, retry, switchMap, tap } from 'rxjs';
import type { Job } from '@photofant/models';
import { JobsService } from '@photofant/services';
import { jobsActions } from './jobs.actions';

@Injectable()
export class JobsEffects {
  private readonly actions$ = inject(Actions);
  private readonly jobsService = inject(JobsService);

  readonly triggerDemo = createEffect(() =>
    this.actions$.pipe(
      ofType(jobsActions.triggerDemo),
      switchMap(() =>
        this.jobsService.triggerDemo().pipe(
          tap(() => { /* SSE liefert den Job-State automatisch */ }),
          catchError(() => of(jobsActions.streamError({ error: 'Demo-Job konnte nicht gestartet werden' }))),
        )
      ),
    ),
    { dispatch: false }
  );

  readonly loadStream = createEffect(() =>
    this.actions$.pipe(
      ofType(jobsActions.loadStream),
      switchMap(() =>
        this.jobsService.streamJobs().pipe(
          map((job: Job) => jobsActions.upsertJob({ job })),
          // Terminal-Error (Browser hat selbst aufgegeben, siehe jobs.service.ts) → nach kurzer
          // Pause eine frische EventSource aufbauen, statt den Stream endgültig sterben zu lassen.
          retry({ delay: 3000 }),
          catchError((error: Error) =>
            of(jobsActions.streamError({ error: error.message }))
          ),
        )
      ),
    )
  );
}
