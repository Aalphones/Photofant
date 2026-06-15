import { createActionGroup, props } from '@ngrx/store';
import type { Density, GroupKey, SortKey, SortOrder } from '@photofant/models';

export const filtersActions = createActionGroup({
  source: 'Filters',
  events: {
    'Set Sort':      props<{ sort: SortKey; order: SortOrder }>(),
    'Set Group':     props<{ group: GroupKey }>(),
    'Set Density':   props<{ density: Density }>(),
    'Set Favourite': props<{ favourite: boolean | null }>(),
  },
});
