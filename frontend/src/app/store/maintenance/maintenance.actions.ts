import { createActionGroup, emptyProps, props } from '@ngrx/store';
import type {
  AppInfo,
  BackupInfo,
  MaintenanceStatus,
  RebuildTarget,
  ReconcileReport,
  RepairAction,
  RepairResponse,
} from '@photofant/models';

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

    'Trigger Rebuild':         props<{ target: RebuildTarget }>(),
    'Trigger Rebuild Success': props<{ target: RebuildTarget; jobId: string }>(),
    'Trigger Rebuild Failure': props<{ target: RebuildTarget; error: string }>(),
    'Rebuild Done':            props<{ target: RebuildTarget }>(),

    'Trigger Thumbnail Rebuild':         emptyProps(),
    'Trigger Thumbnail Rebuild Success': props<{ jobId: string }>(),
    'Trigger Thumbnail Rebuild Failure': props<{ error: string }>(),
    'Thumbnail Rebuild Done':            emptyProps(),

    'Trigger Reprocess':         emptyProps(),
    'Trigger Reprocess Success': props<{ jobId: string; assetCount: number }>(),
    'Trigger Reprocess Failure': props<{ error: string }>(),
    'Reprocess Done':            emptyProps(),

    'Trigger Reembed All':         emptyProps(),
    'Trigger Reembed All Success': props<{ jobId: string }>(),
    'Trigger Reembed All Failure': props<{ error: string }>(),
    'Reembed Done':                emptyProps(),

    'Load Status':             emptyProps(),
    'Load Status Success':     props<{ status: MaintenanceStatus }>(),
    'Load Status Failure':     props<{ error: string }>(),

    'Load App Info':         emptyProps(),
    'Load App Info Success': props<{ appInfo: AppInfo }>(),
    'Load App Info Failure': props<{ error: string }>(),
  },
});
