import { createActionGroup, emptyProps, props } from '@ngrx/store';
import type { PersonDto } from '@photofant/models';

export const personsActions = createActionGroup({
  source: 'Persons',
  events: {
    'Load Persons':           emptyProps(),
    'Load Persons Success':   props<{ persons: PersonDto[] }>(),
    'Load Persons Failure':   props<{ error: string }>(),
    'Rename Person':          props<{ id: number; name: string }>(),
    'Rename Person Success':  props<{ person: PersonDto }>(),
    'Rename Person Failure':  props<{ error: string }>(),
  },
});
