import { createActionGroup, emptyProps, props } from '@ngrx/store';
import type { SearchMode } from '@photofant/models';

export const searchActions = createActionGroup({
  source: 'Search',
  events: {
    'Set Query': props<{ q: string }>(),
    'Set Mode':  props<{ mode: SearchMode }>(),
    'Clear':     emptyProps(),
  },
});
