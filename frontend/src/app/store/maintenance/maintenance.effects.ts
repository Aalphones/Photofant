import { Injectable, inject } from '@angular/core';
import { Actions, createEffect, ofType } from '@ngrx/effects';
import { catchError, filter, map, of, switchMap } from 'rxjs';
import type { HttpErrorResponse } from '@angular/common/http';
import type { AppInfo, BackupInfo, Job, MaintenanceStatus, ReconcileReport, RepairResponse } from '@photofant/models';
import { MaintenanceService } from '@photofant/services';
import { jobsActions } from '../jobs/jobs.actions';
import { maintenanceActions } from './maintenance.actions';

@Injectable()
export class MaintenanceEffects {
  private readonly actions$ = inject(Actions);
  private readonly maintenanceService = inject(MaintenanceService);

  readonly triggerBackup$ = createEffect(() =>
    this.actions$.pipe(
      ofType(maintenanceActions.triggerBackup),
      switchMap(({ targetDir }) =>
        this.maintenanceService.triggerBackup(targetDir ?? undefined).pipe(
          map((response: { job_id: string }) =>
            maintenanceActions.triggerBackupSuccess({ jobId: response.job_id })
          ),
          catchError((error: HttpErrorResponse) =>
            of(maintenanceActions.triggerBackupFailure({ error: error.message }))
          ),
        )
      ),
    )
  );

  readonly loadBackups$ = createEffect(() =>
    this.actions$.pipe(
      ofType(maintenanceActions.loadBackups),
      switchMap(() =>
        this.maintenanceService.listBackups().pipe(
          map((backups: BackupInfo[]) =>
            maintenanceActions.loadBackupsSuccess({ backups })
          ),
          catchError((error: HttpErrorResponse) =>
            of(maintenanceActions.loadBackupsFailure({ error: error.message }))
          ),
        )
      ),
    )
  );

  readonly triggerReconcile$ = createEffect(() =>
    this.actions$.pipe(
      ofType(maintenanceActions.triggerReconcile),
      switchMap(() =>
        this.maintenanceService.triggerReconcile().pipe(
          map((response: { job_id: string }) =>
            maintenanceActions.triggerReconcileSuccess({ jobId: response.job_id })
          ),
          catchError((error: HttpErrorResponse) =>
            of(maintenanceActions.triggerReconcileFailure({ error: error.message }))
          ),
        )
      ),
    )
  );

  readonly loadReport$ = createEffect(() =>
    this.actions$.pipe(
      ofType(maintenanceActions.loadReport),
      switchMap(() =>
        this.maintenanceService.loadReconcileReport().pipe(
          map((report: ReconcileReport) =>
            maintenanceActions.loadReportSuccess({ report })
          ),
          catchError((error: HttpErrorResponse) =>
            of(maintenanceActions.loadReportFailure({ error: error.message }))
          ),
        )
      ),
    )
  );

  readonly repair$ = createEffect(() =>
    this.actions$.pipe(
      ofType(maintenanceActions.repair),
      switchMap(({ actions }) =>
        this.maintenanceService.repair(actions).pipe(
          map((response: RepairResponse) =>
            maintenanceActions.repairSuccess({ actions, response })
          ),
          catchError((error: HttpErrorResponse) =>
            of(maintenanceActions.repairFailure({ error: error.message }))
          ),
        )
      ),
    )
  );

  // When the reconcile scan job finishes, pull the freshly persisted report.
  readonly reconcileJobDone$ = createEffect(() =>
    this.actions$.pipe(
      ofType(jobsActions.upsertJob),
      filter(({ job }: { job: Job }) => job.kind === 'reconcile' && job.state === 'done'),
      map(() => maintenanceActions.loadReport()),
    )
  );

  readonly reconcileJobFailed$ = createEffect(() =>
    this.actions$.pipe(
      ofType(jobsActions.upsertJob),
      filter(({ job }: { job: Job }) => job.kind === 'reconcile' && job.state === 'error'),
      map(({ job }: { job: Job }) =>
        maintenanceActions.triggerReconcileFailure({ error: job.error ?? 'Scan fehlgeschlagen' })
      ),
    )
  );

  readonly triggerRebuild$ = createEffect(() =>
    this.actions$.pipe(
      ofType(maintenanceActions.triggerRebuild),
      switchMap(({ target }) =>
        this.maintenanceService.triggerRebuild(target).pipe(
          map((response: { job_id: string }) =>
            maintenanceActions.triggerRebuildSuccess({ target, jobId: response.job_id })
          ),
          catchError((error: HttpErrorResponse) =>
            of(maintenanceActions.triggerRebuildFailure({ target, error: error.message }))
          ),
        )
      ),
    )
  );

  readonly loadStatus$ = createEffect(() =>
    this.actions$.pipe(
      ofType(maintenanceActions.loadStatus),
      switchMap(() =>
        this.maintenanceService.loadStatus().pipe(
          map((status: MaintenanceStatus) =>
            maintenanceActions.loadStatusSuccess({ status })
          ),
          catchError((error: HttpErrorResponse) =>
            of(maintenanceActions.loadStatusFailure({ error: error.message }))
          ),
        )
      ),
    )
  );

  // When a rebuild job finishes, clear the running flag and refresh the storage stats.
  readonly rebuildJobDone$ = createEffect(() =>
    this.actions$.pipe(
      ofType(jobsActions.upsertJob),
      filter(({ job }: { job: Job }) => job.kind === 'rebuild' && job.state === 'done'),
      switchMap(() => [
        maintenanceActions.rebuildDone({ target: 'thumbnails' }),
        maintenanceActions.loadStatus(),
      ]),
    )
  );

  readonly rebuildJobFailed$ = createEffect(() =>
    this.actions$.pipe(
      ofType(jobsActions.upsertJob),
      filter(({ job }: { job: Job }) => job.kind === 'rebuild' && job.state === 'error'),
      map(({ job }: { job: Job }) =>
        maintenanceActions.triggerRebuildFailure({
          target: 'thumbnails',
          error: job.error ?? 'Rebuild fehlgeschlagen',
        })
      ),
    )
  );

  readonly triggerThumbnailRebuild$ = createEffect(() =>
    this.actions$.pipe(
      ofType(maintenanceActions.triggerThumbnailRebuild),
      switchMap(() =>
        this.maintenanceService.rebuildThumbnails().pipe(
          map((response: { job_id: string }) =>
            maintenanceActions.triggerThumbnailRebuildSuccess({ jobId: response.job_id })
          ),
          catchError((error: HttpErrorResponse) =>
            of(maintenanceActions.triggerThumbnailRebuildFailure({ error: error.message }))
          ),
        )
      ),
    )
  );

  readonly thumbnailRebuildJobDone$ = createEffect(() =>
    this.actions$.pipe(
      ofType(jobsActions.upsertJob),
      filter(({ job }: { job: Job }) => job.kind === 'thumbnail_rebuild' && job.state === 'done'),
      switchMap(() => [
        maintenanceActions.thumbnailRebuildDone(),
        maintenanceActions.loadStatus(),
      ]),
    )
  );

  readonly thumbnailRebuildJobFailed$ = createEffect(() =>
    this.actions$.pipe(
      ofType(jobsActions.upsertJob),
      filter(({ job }: { job: Job }) => job.kind === 'thumbnail_rebuild' && job.state === 'error'),
      map(({ job }: { job: Job }) =>
        maintenanceActions.triggerThumbnailRebuildFailure({ error: job.error ?? 'Rebuild fehlgeschlagen' })
      ),
    )
  );

  readonly loadAppInfo$ = createEffect(() =>
    this.actions$.pipe(
      ofType(maintenanceActions.loadAppInfo),
      switchMap(() =>
        this.maintenanceService.loadAppInfo().pipe(
          map((appInfo: AppInfo) => maintenanceActions.loadAppInfoSuccess({ appInfo })),
          catchError((error: HttpErrorResponse) =>
            of(maintenanceActions.loadAppInfoFailure({ error: error.message }))
          ),
        )
      ),
    )
  );
}
