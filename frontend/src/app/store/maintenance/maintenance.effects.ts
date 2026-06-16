import { Injectable, inject } from '@angular/core';
import { Actions, createEffect, ofType } from '@ngrx/effects';
import { catchError, map, of, switchMap } from 'rxjs';
import type { HttpErrorResponse } from '@angular/common/http';
import type { BackupInfo } from '@photofant/models';
import { MaintenanceService } from '@photofant/services';
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
}
