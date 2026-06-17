import { createSelector } from '@ngrx/store';
import { presetsFeature } from './presets.reducer';
import type { CaptionPresetDto } from '@photofant/models';

const {
  selectPresets,
  selectIsLoading,
  selectError,
} = presetsFeature;

const selectDefaultPreset = createSelector(selectPresets, (presets: CaptionPresetDto[]) =>
  presets.find((preset: CaptionPresetDto) => preset.is_default) ?? null
);

export const presetsSelectors = {
  selectPresets,
  selectIsLoading,
  selectError,
  selectDefaultPreset,
};
