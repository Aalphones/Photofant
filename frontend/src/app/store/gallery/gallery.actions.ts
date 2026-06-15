import { createActionGroup, emptyProps, props } from '@ngrx/store';
import type { AssetDto } from '@photofant/models';

export const galleryActions = createActionGroup({
  source: 'Gallery',
  events: {
    'Request Page':              emptyProps(),
    'Request Next Page':         emptyProps(),
    'Reset':                     emptyProps(),
    'Load Page Success':         props<{ items: AssetDto[]; total: number; page: number; pageSize: number }>(),
    'Load Page Failure':         props<{ error: string }>(),
    'Open Lightbox':             props<{ id: number }>(),
    'Close Lightbox':            emptyProps(),
    'Lightbox Go To':            props<{ id: number }>(),
    'Lightbox Next':             emptyProps(),
    'Lightbox Prev':             emptyProps(),
    'Lightbox Mark Pending Next': emptyProps(),
  },
});
