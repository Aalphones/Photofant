import { createActionGroup, emptyProps, props } from '@ngrx/store';
import type { AssetDto } from '@photofant/models';

export const trashActions = createActionGroup({
  source: 'Trash',
  events: {
    'Load':            emptyProps(),
    'Load Success':    props<{ items: AssetDto[] }>(),
    'Load Failure':    props<{ error: string }>(),
    'Restore':         props<{ id: number }>(),
    'Restore Success': props<{ id: number }>(),
    'Restore Failure': props<{ error: string }>(),
    'Purge':           props<{ id: number }>(),
    'Purge Success':   props<{ id: number }>(),
    'Purge Failure':   props<{ error: string }>(),
    'Empty':           emptyProps(),
    'Empty Success':   emptyProps(),
    'Empty Failure':   props<{ error: string }>(),
  },
});
