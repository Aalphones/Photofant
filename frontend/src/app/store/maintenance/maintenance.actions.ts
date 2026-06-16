import { createActionGroup, emptyProps, props } from '@ngrx/store';
import type { BackupInfo } from '@photofant/models';

export const maintenanceActions = createActionGroup({
  source: 'Maintenance',
  events: {
    'Trigger Backup':         props<{ targetDir: string | null }>(),
    'Trigger Backup Success': props<{ jobId: string }>(),
    'Trigger Backup Failure': props<{ error: string }>(),
    'Load Backups':           emptyProps(),
    'Load Backups Success':   props<{ backups: BackupInfo[] }>(),
    'Load Backups Failure':   props<{ error: string }>(),
  },
});
