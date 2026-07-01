import { createFeature, createReducer, on } from '@ngrx/store';
import type {
  AppInfo,
  BackupInfo,
  MaintenanceStatus,
  RebuildTarget,
  ReconcileReport,
  RepairAction,
  RepairItem,
} from '@photofant/models';
import { maintenanceActions } from './maintenance.actions';

export interface MaintenanceState {
  backups: BackupInfo[];
  isLoadingBackups: boolean;
  isRunningBackup: boolean;
  lastJobId: string | null;
  report: ReconcileReport | null;
  isScanning: boolean;
  isRepairing: boolean;
  rebuildingTarget: RebuildTarget | null;
  isThumbnailRebuilding: boolean;
  status: MaintenanceStatus | null;
  appInfo: AppInfo | null;
  isLoadingAppInfo: boolean;
  error: string | null;
}

const initialState: MaintenanceState = {
  backups: [],
  isLoadingBackups: false,
  isRunningBackup: false,
  lastJobId: null,
  report: null,
  isScanning: false,
  isRepairing: false,
  rebuildingTarget: null,
  isThumbnailRebuilding: false,
  status: null,
  appInfo: null,
  isLoadingAppInfo: false,
  error: null,
};

function repairedItems(actions: RepairAction[], statuses: ('ok' | 'error')[]): RepairItem[] {
  return actions.filter((_action: RepairAction, index: number) => statuses[index] === 'ok').map((action: RepairAction) => action.item);
}

function pruneReport(report: ReconcileReport, removed: RepairItem[]): ReconcileReport {
  const orphanPaths = new Set(removed.filter((item: RepairItem) => item.kind === 'orphan').map((item: RepairItem) => item.path));
  const missingIds = new Set(removed.filter((item: RepairItem) => item.kind === 'missing').map((item: RepairItem) => item.instance_id));
  const driftIds = new Set(removed.filter((item: RepairItem) => item.kind === 'drift').map((item: RepairItem) => item.instance_id));
  const orphanedFaceIds = new Set(removed.filter((item: RepairItem) => item.kind === 'orphaned_face').map((item: RepairItem) => item.face_id));
  const misassignedIds = new Set(removed.filter((item: RepairItem) => item.kind === 'misassigned').map((item: RepairItem) => item.instance_id));
  const ackMissingIds = new Set(removed.filter((item: RepairItem) => item.kind === 'acknowledged_missing').map((item: RepairItem) => item.instance_id));
  const orphanedEditPaths = new Set(removed.filter((item: RepairItem) => item.kind === 'orphaned_edit').map((item: RepairItem) => item.path));
  return {
    ...report,
    orphaned_files: report.orphaned_files.filter((file) => !orphanPaths.has(file.path)),
    missing_files: report.missing_files.filter((file) => !missingIds.has(file.instance_id)),
    path_drift: report.path_drift.filter((file) => !driftIds.has(file.instance_id)),
    orphaned_faces: report.orphaned_faces.filter((face) => !orphanedFaceIds.has(face.face_id)),
    misassigned_instances: report.misassigned_instances.filter((instance) => !misassignedIds.has(instance.instance_id)),
    acknowledged_missing: report.acknowledged_missing.filter((instance) => !ackMissingIds.has(instance.instance_id)),
    orphaned_edits: report.orphaned_edits.filter((file) => !orphanedEditPaths.has(file.path)),
  };
}

export const maintenanceFeature = createFeature({
  name: 'maintenance',
  reducer: createReducer(
    initialState,
    on(maintenanceActions.triggerBackup, (state: MaintenanceState) => ({
      ...state,
      isRunningBackup: true,
      error: null,
    })),
    on(maintenanceActions.triggerBackupSuccess, (state: MaintenanceState, { jobId }) => ({
      ...state,
      isRunningBackup: false,
      lastJobId: jobId,
    })),
    on(maintenanceActions.triggerBackupFailure, (state: MaintenanceState, { error }) => ({
      ...state,
      isRunningBackup: false,
      error,
    })),
    on(maintenanceActions.loadBackups, (state: MaintenanceState) => ({
      ...state,
      isLoadingBackups: true,
      error: null,
    })),
    on(maintenanceActions.loadBackupsSuccess, (state: MaintenanceState, { backups }) => ({
      ...state,
      isLoadingBackups: false,
      backups,
    })),
    on(maintenanceActions.loadBackupsFailure, (state: MaintenanceState, { error }) => ({
      ...state,
      isLoadingBackups: false,
      error,
    })),

    on(maintenanceActions.triggerReconcile, (state: MaintenanceState) => ({
      ...state,
      isScanning: true,
      error: null,
    })),
    on(maintenanceActions.triggerReconcileSuccess, (state: MaintenanceState, { jobId }) => ({
      ...state,
      lastJobId: jobId,
    })),
    on(maintenanceActions.triggerReconcileFailure, (state: MaintenanceState, { error }) => ({
      ...state,
      isScanning: false,
      error,
    })),
    on(maintenanceActions.loadReportSuccess, (state: MaintenanceState, { report }) => ({
      ...state,
      isScanning: false,
      report,
    })),
    on(maintenanceActions.loadReportFailure, (state: MaintenanceState, { error }) => ({
      ...state,
      isScanning: false,
      error,
    })),
    on(maintenanceActions.repair, (state: MaintenanceState) => ({
      ...state,
      isRepairing: true,
      error: null,
    })),
    on(maintenanceActions.repairSuccess, (state: MaintenanceState, { actions, response }) => ({
      ...state,
      isRepairing: false,
      report: state.report
        ? pruneReport(state.report, repairedItems(actions, response.results.map((result) => result.status)))
        : state.report,
    })),
    on(maintenanceActions.repairFailure, (state: MaintenanceState, { error }) => ({
      ...state,
      isRepairing: false,
      error,
    })),

    on(maintenanceActions.triggerRebuild, (state: MaintenanceState, { target }) => ({
      ...state,
      rebuildingTarget: target,
      error: null,
    })),
    on(maintenanceActions.triggerRebuildSuccess, (state: MaintenanceState, { jobId }) => ({
      ...state,
      lastJobId: jobId,
    })),
    on(maintenanceActions.triggerRebuildFailure, (state: MaintenanceState, { error }) => ({
      ...state,
      rebuildingTarget: null,
      error,
    })),
    on(maintenanceActions.rebuildDone, (state: MaintenanceState) => ({
      ...state,
      rebuildingTarget: null,
    })),

    on(maintenanceActions.triggerThumbnailRebuild, (state: MaintenanceState) => ({
      ...state,
      isThumbnailRebuilding: true,
      error: null,
    })),
    on(maintenanceActions.triggerThumbnailRebuildSuccess, (state: MaintenanceState) => ({
      ...state,
    })),
    on(maintenanceActions.triggerThumbnailRebuildFailure, (state: MaintenanceState, { error }) => ({
      ...state,
      isThumbnailRebuilding: false,
      error,
    })),
    on(maintenanceActions.thumbnailRebuildDone, (state: MaintenanceState) => ({
      ...state,
      isThumbnailRebuilding: false,
    })),

    on(maintenanceActions.loadStatusSuccess, (state: MaintenanceState, { status }) => ({
      ...state,
      status,
    })),
    on(maintenanceActions.loadStatusFailure, (state: MaintenanceState, { error }) => ({
      ...state,
      error,
    })),

    on(maintenanceActions.loadAppInfo, (state: MaintenanceState) => ({
      ...state,
      isLoadingAppInfo: true,
      error: null,
    })),
    on(maintenanceActions.loadAppInfoSuccess, (state: MaintenanceState, { appInfo }) => ({
      ...state,
      isLoadingAppInfo: false,
      appInfo,
    })),
    on(maintenanceActions.loadAppInfoFailure, (state: MaintenanceState, { error }) => ({
      ...state,
      isLoadingAppInfo: false,
      error,
    })),
  ),
});
