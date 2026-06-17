import { createActionGroup, emptyProps, props } from '@ngrx/store';
import type { TagListItem } from '@photofant/models';

export const tagsActions = createActionGroup({
  source: 'Tags',
  events: {
    'Load':              emptyProps(),
    'Load Success':      props<{ items: TagListItem[] }>(),
    'Load Failure':      props<{ error: string }>(),
    'Rename':            props<{ id: number; name: string }>(),
    'Rename Success':    props<{ item: TagListItem }>(),
    'Rename Failure':    props<{ error: string }>(),
    'Merge':             props<{ from_ids: number[]; into_id: number }>(),
    'Merge Success':     emptyProps(),
    'Merge Failure':     props<{ error: string }>(),
    'Bulk Tag':          props<{ asset_ids: number[]; add: string[]; remove: number[] }>(),
    'Bulk Tag Success':  emptyProps(),
    'Bulk Tag Failure':  props<{ error: string }>(),
  },
});
