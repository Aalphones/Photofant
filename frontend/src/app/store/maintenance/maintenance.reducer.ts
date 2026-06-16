import { createFeature, createReducer, on } from '@ngrx/store';
import type { BackupInfo } from '@photofant/models';
import { maintenanceActions } from './maintenance.actions';

export interface MaintenanceState {
  backups: BackupInfo[];
  isLoadingBackups: boolean;
  isRunningBackup: boolean;
  lastJobId: string | null;
  error: string | null;
}

const initialState: MaintenanceState = {
  backups: [],
  isLoadingBackups: false,
  isRunningBackup: false,
  lastJobId: null,
  error: null,
};

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
  ),
});
