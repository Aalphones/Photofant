import { maintenanceFeature } from './maintenance.reducer';

const {
  selectBackups,
  selectIsLoadingBackups,
  selectIsRunningBackup,
  selectLastJobId,
  selectReport,
  selectIsScanning,
  selectIsRepairing,
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
  selectError,
};
