import { createFeature, createReducer, on } from '@ngrx/store';
import type { ModelDto, CapabilitiesDto, ModelBindError } from '@photofant/models';
import { modelsActions } from './models.actions';

export interface ModelsState {
  models: ModelDto[];
  capabilities: CapabilitiesDto | null;
  modelsDir: string | null;
  isLoading: boolean;
  pendingDownloads: string[];
  pendingBinds: string[];
  bindError: ModelBindError | null;
  error: string | null;
}

const initialState: ModelsState = {
  models: [],
  capabilities: null,
  modelsDir: null,
  isLoading: false,
  pendingDownloads: [],
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

    on(modelsActions.loadConfigSuccess, (state: ModelsState, { modelsDir }) =>
      ({ ...state, modelsDir })
    ),

    on(modelsActions.downloadModel, (state: ModelsState, { manifestId }) => ({
      ...state,
      pendingDownloads: [...state.pendingDownloads, manifestId],
    })),
    on(modelsActions.downloadModelSuccess, (state: ModelsState, { manifestId }) => ({
      ...state,
      pendingDownloads: state.pendingDownloads.filter((id: string) => id !== manifestId),
    })),
    on(modelsActions.downloadModelFailure, (state: ModelsState, { manifestId }) => ({
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
  ),
});
