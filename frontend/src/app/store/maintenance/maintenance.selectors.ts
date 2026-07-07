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
  selectIsThumbnailRebuilding,
  selectIsReembedding,
  selectStatus,
  selectAppInfo,
  selectIsLoadingAppInfo,
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
  selectIsThumbnailRebuilding,
  selectIsReembedding,
  selectStatus,
  selectAppInfo,
  selectIsLoadingAppInfo,
  selectError,
};
