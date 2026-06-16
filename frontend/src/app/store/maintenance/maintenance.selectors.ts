import { maintenanceFeature } from './maintenance.reducer';

const {
  selectBackups,
  selectIsLoadingBackups,
  selectIsRunningBackup,
  selectLastJobId,
  selectReport,
  selectIsScanning,
  selectIsRepairing,
  selectRebuildingTarget,
  selectStatus,
  selectError,
} = maintenanceFeature;

export const maintenanceSelectors = {
  selectBackups,
  selectIsLoadingBackups,
  selectIsRunningBackup,
  selectLastJobId,
  selectReport,
  selectIsScanning,
  selectIsRepairing,
  selectRebuildingTarget,
  selectStatus,
  selectError,
};
