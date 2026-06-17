import { createFeature, createReducer, on } from '@ngrx/store';
import type { CaptionPresetDto } from '@photofant/models';
import { presetsActions } from './presets.actions';

export interface PresetsState {
  presets: CaptionPresetDto[];
  isLoading: boolean;
  error: string | null;
}

const initialState: PresetsState = {
  presets: [],
  isLoading: false,
  error: null,
};

export const presetsFeature = createFeature({
  name: 'presets',
  reducer: createReducer(
    initialState,

    on(presetsActions.loadPresets, (state: PresetsState) =>
      ({ ...state, isLoading: true, error: null })
    ),
    on(presetsActions.loadPresetsSuccess, (state: PresetsState, { presets }) =>
      ({ ...state, isLoading: false, presets })
    ),
    on(presetsActions.loadPresetsFailure, (state: PresetsState, { error }) =>
      ({ ...state, isLoading: false, error })
    ),

    on(presetsActions.createPresetSuccess, (state: PresetsState, { preset }) =>
      ({ ...state, presets: [...state.presets, preset] })
    ),

    on(presetsActions.updatePresetSuccess, (state: PresetsState, { preset }) => ({
      ...state,
      presets: state.presets.map((existing: CaptionPresetDto) => {
        if (preset.is_default && existing.id !== preset.id && existing.model_id === preset.model_id) {
          return { ...existing, is_default: false };
        }
        return existing.id === preset.id ? preset : existing;
      }),
    })),

    on(presetsActions.deletePresetSuccess, (state: PresetsState, { id }) => ({
      ...state,
      presets: state.presets.filter((preset: CaptionPresetDto) => preset.id !== id),
    })),
  ),
});
