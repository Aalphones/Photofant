import { createActionGroup, emptyProps, props } from '@ngrx/store';
import type { AssetDto, Facets } from '@photofant/models';

export const galleryActions = createActionGroup({
  source: 'Gallery',
  events: {
    'Request Page':              emptyProps(),
    'Request Next Page':         emptyProps(),
    'Reset':                     emptyProps(),
    'Load Page Success':         props<{ items: AssetDto[]; total: number; page: number; pageSize: number; facets: Facets }>(),
    'Load Page Failure':         props<{ error: string }>(),
    'Open Lightbox':             props<{ id: number }>(),
    'Close Lightbox':            emptyProps(),
    'Lightbox Go To':            props<{ id: number }>(),
    'Lightbox Next':             emptyProps(),
    'Lightbox Prev':             emptyProps(),
    'Lightbox Mark Pending Next': emptyProps(),
    'Toggle Favourite':          props<{ id: number; value: boolean }>(),
    'Toggle Favourite Success':  props<{ asset: AssetDto }>(),
    'Toggle Favourite Failure':  props<{ id: number; previous: boolean }>(),
    'Delete Asset':              props<{ id: number }>(),
    'Delete Asset Success':      props<{ id: number }>(),
    'Delete Asset Failure':      props<{ error: string }>(),
  },
});
