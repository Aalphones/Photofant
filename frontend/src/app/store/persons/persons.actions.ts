import { createActionGroup, emptyProps, props } from '@ngrx/store';
import type { ClusterResult, PersonDto, MergeResult, SplitResult } from '@photofant/models';

export const personsActions = createActionGroup({
  source: 'Persons',
  events: {
    'Load Persons':              emptyProps(),
    'Load Persons Success':      props<{ persons: PersonDto[] }>(),
    'Load Persons Failure':      props<{ error: string }>(),
    'Rename Person':             props<{ id: number; name: string }>(),
    'Rename Person Success':     props<{ person: PersonDto }>(),
    'Rename Person Failure':     props<{ error: string }>(),
    'Merge Persons':             props<{ fromId: number; intoId: number }>(),
    'Merge Persons Success':     props<{ result: MergeResult }>(),
    'Merge Persons Failure':     props<{ error: string }>(),
    'Split Person':              props<{ personId: number; faceIds: number[] }>(),
    'Split Person Success':      props<{ result: SplitResult }>(),
    'Split Person Failure':      props<{ error: string }>(),
    'Trigger Clustering':        emptyProps(),
    'Trigger Clustering Success': props<{ result: ClusterResult }>(),
    'Trigger Clustering Failure': props<{ error: string }>(),
    'Create Person':              props<{ name: string }>(),
    'Create Person Success':      props<{ person: PersonDto }>(),
    'Create Person Failure':      props<{ error: string }>(),
  },
});
