import { createActionGroup, emptyProps, props } from '@ngrx/store';
import type { Density, MediaType, SortKey, SortOrder } from '@photofant/models';

export const filtersActions = createActionGroup({
  source: 'Filters',
  events: {
    'Set Sort':         props<{ sort: SortKey; order: SortOrder }>(),
    'Set Density':      props<{ density: Density }>(),
    'Set Favourite':    props<{ favourite: boolean | null }>(),
    'Set Sources':      props<{ sources: string[] }>(),
    'Set Quality Min':  props<{ qualityMin: number }>(),
    'Set Tag Ids':      props<{ tagIds: number[] }>(),
    'Set Collection Id': props<{ collectionId: number | null }>(),
    'Set Person Id':     props<{ personId: number | null }>(),
    'Set Framings':      props<{ framings: string[] }>(),
    'Set Has Faces':     props<{ hasFaces: boolean | null }>(),
    'Set Classification Label Ids': props<{ classificationLabelIds: number[] }>(),
    'Set Media Type':    props<{ mediaType: MediaType }>(),
    'Clear All Filters': emptyProps(),
  },
});
