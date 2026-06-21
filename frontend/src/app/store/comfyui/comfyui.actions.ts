import { createActionGroup, emptyProps, props } from '@ngrx/store';
import type { ComfyUIConfig } from '@photofant/models';

export const comfyuiActions = createActionGroup({
  source: 'ComfyUI',
  events: {
    'Load Config':          emptyProps(),
    'Load Config Success':  props<{ config: ComfyUIConfig }>(),
    'Load Config Failure':  props<{ error: string }>(),
    'Save Config':          props<{ config: ComfyUIConfig }>(),
    'Save Config Success':  props<{ config: ComfyUIConfig }>(),
    'Save Config Failure':  props<{ error: string }>(),
    'Test Connection':         emptyProps(),
    'Test Connection Success': props<{ ok: boolean; detail: string }>(),
    'Test Connection Failure': props<{ error: string }>(),
    'Clear Test Result':    emptyProps(),
  },
});
