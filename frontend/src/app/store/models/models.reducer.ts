import { createFeature, createReducer, on } from '@ngrx/store';
import type { ModelDto, CapabilitiesDto, ModelBindError, ProcessingConfig, ShortcutConfig } from '@photofant/models';
import { PROCESSING_CONFIG_DEFAULTS } from '@photofant/models';
import { modelsActions } from './models.actions';

export interface ModelsState {
  models: ModelDto[];
  capabilities: CapabilitiesDto | null;
  modelsDir: string | null;
  dataRoot: string | null;
  rebootRequired: boolean;
  processingConfig: ProcessingConfig;
  keyboardShortcuts: ShortcutConfig | null;
  isLoading: boolean;
  pendingDownloads: string[];
  downloadJobIds: Record<string, string>;
  pendingBinds: string[];
  bindError: ModelBindError | null;
  error: string | null;
}

const initialState: ModelsState = {
  models: [],
  capabilities: null,
  modelsDir: null,
  dataRoot: null,
  rebootRequired: false,
  processingConfig: PROCESSING_CONFIG_DEFAULTS,
  keyboardShortcuts: null,
  isLoading: false,
  pendingDownloads: [],
  downloadJobIds: {},
  pendingBinds: [],
  bindError: null,
  error: null,
};

export const modelsFeature = createFeature({
  name: 'models',
  reducer: createReducer(
    initialState,

    on(modelsActions.loadModels, (state: ModelsState) =>
      ({ ...state, isLoading: true, error: null })
    ),
    on(modelsActions.loadModelsSuccess, (state: ModelsState, { models }) =>
      ({ ...state, isLoading: false, models })
    ),
    on(modelsActions.loadModelsFailure, (state: ModelsState, { error }) =>
      ({ ...state, isLoading: false, error })
    ),

    on(modelsActions.loadCapabilitiesSuccess, (state: ModelsState, { capabilities }) =>
      ({ ...state, capabilities })
    ),

    on(modelsActions.loadConfigSuccess, (state: ModelsState, { modelsDir, dataRoot, processingConfig, keyboardShortcuts }) =>
      ({ ...state, modelsDir, dataRoot, processingConfig, keyboardShortcuts })
    ),

    on(modelsActions.updateProcessingConfigSuccess, (state: ModelsState, { processingConfig }) =>
      ({ ...state, processingConfig })
    ),

    on(modelsActions.updateShortcutsSuccess, (state: ModelsState, { config }) =>
      ({ ...state, keyboardShortcuts: config })
    ),

    on(modelsActions.downloadModel, (state: ModelsState, { manifestId }) => {
      // Clear stale error job entry on retry, add to pending
      const { [manifestId]: _, ...remainingJobs } = state.downloadJobIds;
      return {
        ...state,
        pendingDownloads: [...state.pendingDownloads, manifestId],
        downloadJobIds: _ !== undefined ? remainingJobs : state.downloadJobIds,
      };
    }),
    // downloadModelSuccess: job is now running — keep in pendingDownloads, store jobId
    on(modelsActions.downloadModelSuccess, (state: ModelsState, { jobId, manifestId }) => ({
      ...state,
      downloadJobIds: { ...state.downloadJobIds, [manifestId]: jobId },
    })),
    // HTTP POST failed before job was created
    on(modelsActions.downloadModelFailure, (state: ModelsState, { manifestId }) => ({
      ...state,
      pendingDownloads: state.pendingDownloads.filter((id: string) => id !== manifestId),
    })),

    // Background job completed successfully
    on(modelsActions.downloadJobCompleted, (state: ModelsState, { manifestId }) => {
      const { [manifestId]: _, ...remainingJobs } = state.downloadJobIds;
      return {
        ...state,
        pendingDownloads: state.pendingDownloads.filter((id: string) => id !== manifestId),
        downloadJobIds: _ !== undefined ? remainingJobs : state.downloadJobIds,
      };
    }),
    // Background job failed — remove from pending but keep jobId so error is visible
    on(modelsActions.downloadJobFailed, (state: ModelsState, { manifestId }) => ({
      ...state,
      pendingDownloads: state.pendingDownloads.filter((id: string) => id !== manifestId),
    })),

    on(modelsActions.registerLocal, (state: ModelsState, { manifestId }) => ({
      ...state,
      pendingBinds: [...state.pendingBinds, manifestId],
      bindError: null,
    })),
    on(modelsActions.registerLocalSuccess, (state: ModelsState, { model }) => ({
      ...state,
      pendingBinds: state.pendingBinds.filter((id: string) => id !== model.id),
      models: state.models.map((existing: ModelDto) =>
        existing.id === model.id ? model : existing
      ),
      bindError: null,
    })),
    on(modelsActions.registerLocalFailure, (state: ModelsState, { manifestId, error, code }) => ({
      ...state,
      pendingBinds: state.pendingBinds.filter((id: string) => id !== manifestId),
      bindError: { manifestId, code, message: error },
    })),
    on(modelsActions.clearBindError, (state: ModelsState) =>
      ({ ...state, bindError: null })
    ),

    on(modelsActions.deleteModelSuccess, (state: ModelsState, { manifestId }) => ({
      ...state,
      models: state.models.map((model: ModelDto) =>
        model.id === manifestId
          ? { ...model, status: 'missing' as const, path: null, sha256: null, enabled: false }
          : model
      ),
    })),

    on(modelsActions.updateModelsDirSuccess, (state: ModelsState, { modelsDir }) =>
      ({ ...state, modelsDir })
    ),

    on(modelsActions.updateDataRootSuccess, (state: ModelsState, { dataRoot }) =>
      ({ ...state, dataRoot, rebootRequired: true })
    ),
  ),
});
