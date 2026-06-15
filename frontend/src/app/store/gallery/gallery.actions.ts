import { createActionGroup, emptyProps, props } from '@ngrx/store';
import type { AssetDto } from '@photofant/models';

export const galleryActions = createActionGroup({
  source: 'Gallery',
  events: {
    'Request Page':      emptyProps(),
    'Request Next Page': emptyProps(),
    'Reset':             emptyProps(),
    'Load Page Success': props<{ items: AssetDto[]; total: number; page: number; pageSize: number }>(),
    'Load Page Failure': props<{ error: string }>(),
  },
});
