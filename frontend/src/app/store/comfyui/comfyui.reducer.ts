import { createFeature, createReducer, on } from '@ngrx/store';
import type { ComfyUIConfig, ComfyUIWorkflow } from '@photofant/models';
import { COMFYUI_CONFIG_DEFAULTS } from '@photofant/models';
import { comfyuiActions } from './comfyui.actions';

export interface TestResult {
  ok: boolean;
  detail: string;
}

export interface ComfyUIState {
  config: ComfyUIConfig;
  isLoading: boolean;
  isSaving: boolean;
  isTesting: boolean;
  testResult: TestResult | null;
  error: string | null;
  workflows: ComfyUIWorkflow[];
  isLoadingWorkflows: boolean;
  isCreatingWorkflow: boolean;
  selectedWorkflowId: string | null;
  workflowError: string | null;
}

const initialState: ComfyUIState = {
  config: COMFYUI_CONFIG_DEFAULTS,
  isLoading: false,
  isSaving: false,
  isTesting: false,
  testResult: null,
  error: null,
  workflows: [],
  isLoadingWorkflows: false,
  isCreatingWorkflow: false,
  selectedWorkflowId: null,
  workflowError: null,
};

function replaceWorkflow(workflows: ComfyUIWorkflow[], updated: ComfyUIWorkflow): ComfyUIWorkflow[] {
  return workflows.map((workflow: ComfyUIWorkflow) => workflow.key === updated.key ? updated : workflow);
}

export const comfyuiFeature = createFeature({
  name: 'comfyui',
  reducer: createReducer(
    initialState,

    on(comfyuiActions.loadConfig, (state: ComfyUIState) =>
      ({ ...state, isLoading: true, error: null })
    ),
    on(comfyuiActions.loadConfigSuccess, (state: ComfyUIState, { config }) =>
      ({ ...state, isLoading: false, config })
    ),
    on(comfyuiActions.loadConfigFailure, (state: ComfyUIState, { error }) =>
      ({ ...state, isLoading: false, error })
    ),

    on(comfyuiActions.saveConfig, (state: ComfyUIState) =>
      ({ ...state, isSaving: true, error: null, testResult: null })
    ),
    on(comfyuiActions.saveConfigSuccess, (state: ComfyUIState, { config }) =>
      ({ ...state, isSaving: false, config })
    ),
    on(comfyuiActions.saveConfigFailure, (state: ComfyUIState, { error }) =>
      ({ ...state, isSaving: false, error })
    ),

    on(comfyuiActions.testConnection, (state: ComfyUIState) =>
      ({ ...state, isTesting: true, testResult: null, error: null })
    ),
    on(comfyuiActions.testConnectionSuccess, (state: ComfyUIState, { ok, detail }) =>
      ({ ...state, isTesting: false, testResult: { ok, detail } })
    ),
    on(comfyuiActions.testConnectionFailure, (state: ComfyUIState, { error }) =>
      ({ ...state, isTesting: false, error })
    ),

    on(comfyuiActions.clearTestResult, (state: ComfyUIState) =>
      ({ ...state, testResult: null })
    ),

    // Workflows
    on(comfyuiActions.loadWorkflows, (state: ComfyUIState) =>
      ({ ...state, isLoadingWorkflows: true, workflowError: null })
    ),
    on(comfyuiActions.loadWorkflowsSuccess, (state: ComfyUIState, { workflows }) =>
      ({ ...state, isLoadingWorkflows: false, workflows })
    ),
    on(comfyuiActions.loadWorkflowsFailure, (state: ComfyUIState, { error }) =>
      ({ ...state, isLoadingWorkflows: false, workflowError: error })
    ),

    on(comfyuiActions.createWorkflow, (state: ComfyUIState) =>
      ({ ...state, isCreatingWorkflow: true, workflowError: null })
    ),
    on(comfyuiActions.createWorkflowSuccess, (state: ComfyUIState, { workflow }) =>
      ({ ...state, isCreatingWorkflow: false, workflows: [...state.workflows, workflow], selectedWorkflowId: workflow.key })
    ),
    on(comfyuiActions.createWorkflowFailure, (state: ComfyUIState, { error }) =>
      ({ ...state, isCreatingWorkflow: false, workflowError: error })
    ),

    on(comfyuiActions.updateWorkflowSuccess, (state: ComfyUIState, { workflow }) =>
      ({ ...state, workflows: replaceWorkflow(state.workflows, workflow) })
    ),
    on(comfyuiActions.updateWorkflowFailure, (state: ComfyUIState, { error }) =>
      ({ ...state, workflowError: error })
    ),

    on(comfyuiActions.deleteWorkflowSuccess, (state: ComfyUIState, { workflowId }) => ({
      ...state,
      workflows: state.workflows.filter((workflow: ComfyUIWorkflow) => workflow.key !== workflowId),
      selectedWorkflowId: state.selectedWorkflowId === workflowId ? null : state.selectedWorkflowId,
    })),
    on(comfyuiActions.deleteWorkflowFailure, (state: ComfyUIState, { error }) =>
      ({ ...state, workflowError: error })
    ),

    on(comfyuiActions.duplicateWorkflowSuccess, (state: ComfyUIState, { workflow }) =>
      ({ ...state, workflows: [...state.workflows, workflow] })
    ),
    on(comfyuiActions.duplicateWorkflowFailure, (state: ComfyUIState, { error }) =>
      ({ ...state, workflowError: error })
    ),

    on(comfyuiActions.redetectInputsSuccess, (state: ComfyUIState, { workflow }) =>
      ({ ...state, workflows: replaceWorkflow(state.workflows, workflow) })
    ),
    on(comfyuiActions.redetectInputsFailure, (state: ComfyUIState, { error }) =>
      ({ ...state, workflowError: error })
    ),

    on(comfyuiActions.selectWorkflow, (state: ComfyUIState, { workflowId }) =>
      ({ ...state, selectedWorkflowId: workflowId })
    ),

    on(comfyuiActions.clearWorkflowError, (state: ComfyUIState) =>
      ({ ...state, workflowError: null })
    ),
  ),
});
