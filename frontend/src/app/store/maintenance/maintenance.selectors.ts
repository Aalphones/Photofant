import { maintenanceFeature } from './maintenance.reducer';

const {
  selectBackups,
  selectIsLoadingBackups,
  selectIsRunningBackup,
  selectLastJobId,
  selectError,
} = maintenanceFeature;

export const maintenanceSelectors = {
  selectBackups,
  selectIsLoadingBackups,
  selectIsRunningBackup,
  selectLastJobId,
  selectError,
};
