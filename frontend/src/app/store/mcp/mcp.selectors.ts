import { mcpFeature } from './mcp.reducer';

const {
  selectConfig,
  selectIsLoading,
  selectIsSaving,
  selectError,
} = mcpFeature;

export const mcpSelectors = {
  selectConfig,
  selectIsLoading,
  selectIsSaving,
  selectError,
};
