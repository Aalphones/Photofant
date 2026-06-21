import { createFeature, createReducer, on } from '@ngrx/store';
import type { ComfyUIConfig } from '@photofant/models';
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
}

const initialState: ComfyUIState = {
  config: COMFYUI_CONFIG_DEFAULTS,
  isLoading: false,
  isSaving: false,
  isTesting: false,
  testResult: null,
  error: null,
};

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
  ),
});
