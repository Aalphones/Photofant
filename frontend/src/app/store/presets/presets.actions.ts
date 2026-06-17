import { createActionGroup, emptyProps, props } from '@ngrx/store';
import type { CaptionPresetDto, CaptionPresetCreate, CaptionPresetUpdate } from '@photofant/models';

export const presetsActions = createActionGroup({
  source: 'Presets',
  events: {
    'Load Presets':           emptyProps(),
    'Load Presets Success':   props<{ presets: CaptionPresetDto[] }>(),
    'Load Presets Failure':   props<{ error: string }>(),

    'Create Preset':          props<{ body: CaptionPresetCreate }>(),
    'Create Preset Success':  props<{ preset: CaptionPresetDto }>(),
    'Create Preset Failure':  props<{ error: string }>(),

    'Update Preset':          props<{ id: number; body: CaptionPresetUpdate }>(),
    'Update Preset Success':  props<{ preset: CaptionPresetDto }>(),
    'Update Preset Failure':  props<{ error: string }>(),

    'Delete Preset':          props<{ id: number }>(),
    'Delete Preset Success':  props<{ id: number }>(),
    'Delete Preset Failure':  props<{ error: string }>(),
  },
});
