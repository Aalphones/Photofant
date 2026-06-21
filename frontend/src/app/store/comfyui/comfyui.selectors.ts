import { createSelector } from '@ngrx/store';
import { comfyuiFeature } from './comfyui.reducer';

const {
  selectConfig,
  selectIsLoading,
  selectIsSaving,
  selectIsTesting,
  selectTestResult,
  selectError,
} = comfyuiFeature;

const selectComfyuiReady = createSelector(
  selectConfig,
  selectTestResult,
  (config, testResult) => config.enabled && testResult?.ok === true
);

export const comfyuiSelectors = {
  selectConfig,
  selectIsLoading,
  selectIsSaving,
  selectIsTesting,
  selectTestResult,
  selectError,
  selectComfyuiReady,
};
