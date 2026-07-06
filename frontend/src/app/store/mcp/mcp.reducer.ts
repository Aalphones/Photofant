import { createFeature, createReducer, on } from '@ngrx/store';
import type { McpConfig } from '@photofant/models';
import { MCP_CONFIG_DEFAULTS } from '@photofant/models';
import { mcpActions } from './mcp.actions';

export interface McpState {
  config: McpConfig;
  isLoading: boolean;
  isSaving: boolean;
  error: string | null;
}

const initialState: McpState = {
  config: MCP_CONFIG_DEFAULTS,
  isLoading: false,
  isSaving: false,
  error: null,
};

export const mcpFeature = createFeature({
  name: 'mcp',
  reducer: createReducer(
    initialState,

    on(mcpActions.loadConfig, (state: McpState) =>
      ({ ...state, isLoading: true, error: null })
    ),
    on(mcpActions.loadConfigSuccess, (state: McpState, { config }) =>
      ({ ...state, isLoading: false, config })
    ),
    on(mcpActions.loadConfigFailure, (state: McpState, { error }) =>
      ({ ...state, isLoading: false, error })
    ),

    on(mcpActions.saveConfig, (state: McpState) =>
      ({ ...state, isSaving: true, error: null })
    ),
    on(mcpActions.saveConfigSuccess, (state: McpState, { config }) =>
      ({ ...state, isSaving: false, config })
    ),
    on(mcpActions.saveConfigFailure, (state: McpState, { error }) =>
      ({ ...state, isSaving: false, error })
    ),
  ),
});
