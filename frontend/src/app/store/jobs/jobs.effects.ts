import { Injectable, inject } from '@angular/core';
import { Actions, createEffect, ofType } from '@ngrx/effects';
import { catchError, map, of, switchMap } from 'rxjs';
import type { Job } from '@photofant/models';
import { JobsService } from '@photofant/services';
import { jobsActions } from './jobs.actions';

@Injectable()
export class JobsEffects {
  private readonly actions$ = inject(Actions);
  private readonly jobsService = inject(JobsService);

  readonly loadStream = createEffect(() =>
    this.actions$.pipe(
      ofType(jobsActions.loadStream),
      switchMap(() =>
        this.jobsService.streamJobs().pipe(
          map((job: Job) => jobsActions.upsertJob({ job })),
          catchError((error: Error) =>
            of(jobsActions.streamError({ error: error.message }))
          ),
        )
      ),
    )
  );
}
