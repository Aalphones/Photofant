import { createActionGroup, emptyProps, props } from '@ngrx/store';
import type { PersonDto, MergeResult, SplitResult } from '@photofant/models';

export const personsActions = createActionGroup({
  source: 'Persons',
  events: {
    'Load Persons':           emptyProps(),
    'Load Persons Success':   props<{ persons: PersonDto[] }>(),
    'Load Persons Failure':   props<{ error: string }>(),
    'Rename Person':          props<{ id: number; name: string }>(),
    'Rename Person Success':  props<{ person: PersonDto }>(),
    'Rename Person Failure':  props<{ error: string }>(),
    'Merge Persons':          props<{ fromId: number; intoId: number }>(),
    'Merge Persons Success':  props<{ result: MergeResult }>(),
    'Merge Persons Failure':  props<{ error: string }>(),
    'Split Person':           props<{ personId: number; faceIds: number[] }>(),
    'Split Person Success':   props<{ result: SplitResult }>(),
    'Split Person Failure':   props<{ error: string }>(),
  },
});
