import { createActionGroup, emptyProps, props } from '@ngrx/store';
import type { BackupInfo, ReconcileReport, RepairAction, RepairResponse } from '@photofant/models';

export const maintenanceActions = createActionGroup({
  source: 'Maintenance',
  events: {
    'Trigger Backup':         props<{ targetDir: string | null }>(),
    'Trigger Backup Success': props<{ jobId: string }>(),
    'Trigger Backup Failure': props<{ error: string }>(),
    'Load Backups':           emptyProps(),
    'Load Backups Success':   props<{ backups: BackupInfo[] }>(),
    'Load Backups Failure':   props<{ error: string }>(),

    'Trigger Reconcile':         emptyProps(),
    'Trigger Reconcile Success': props<{ jobId: string }>(),
    'Trigger Reconcile Failure': props<{ error: string }>(),
    'Load Report':               emptyProps(),
    'Load Report Success':       props<{ report: ReconcileReport }>(),
    'Load Report Failure':       props<{ error: string }>(),
    'Repair':                    props<{ actions: RepairAction[] }>(),
    'Repair Success':            props<{ actions: RepairAction[]; response: RepairResponse }>(),
    'Repair Failure':            props<{ error: string }>(),
  },
});
