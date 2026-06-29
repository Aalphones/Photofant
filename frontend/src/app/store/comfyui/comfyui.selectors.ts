import { createSelector } from '@ngrx/store';
import type { ComfyUIWorkflow } from '@photofant/models';
import { comfyuiFeature } from './comfyui.reducer';

const {
  selectConfig,
  selectIsLoading,
  selectIsSaving,
  selectIsTesting,
  selectTestResult,
  selectError,
  selectWorkflows,
  selectIsLoadingWorkflows,
  selectSelectedWorkflowId,
  selectWorkflowError,
} = comfyuiFeature;

const selectComfyuiReady = createSelector(
  selectConfig,
  selectTestResult,
  (config, testResult) => config.enabled && testResult?.ok === true
);

const selectSelectedWorkflow = createSelector(
  selectWorkflows,
  selectSelectedWorkflowId,
  (workflows: ComfyUIWorkflow[], selectedId: string | null) =>
    selectedId !== null ? workflows.find((workflow: ComfyUIWorkflow) => workflow.key === selectedId) ?? null : null
);

const selectActiveWorkflows = createSelector(
  selectWorkflows,
  (workflows: ComfyUIWorkflow[]) => workflows.filter((workflow: ComfyUIWorkflow) => workflow.isValid)
);

export const comfyuiSelectors = {
  selectConfig,
  selectIsLoading,
  selectIsSaving,
  selectIsTesting,
  selectTestResult,
  selectError,
  selectComfyuiReady,
  selectWorkflows,
  selectIsLoadingWorkflows,
  selectSelectedWorkflowId,
  selectSelectedWorkflow,
  selectActiveWorkflows,
  selectWorkflowError,
};
