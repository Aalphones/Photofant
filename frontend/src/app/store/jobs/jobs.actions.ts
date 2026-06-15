import { createActionGroup, emptyProps, props } from '@ngrx/store';
import type { Job } from '@photofant/models';

export const jobsActions = createActionGroup({
  source: 'Jobs',
  events: {
    'Load Stream':  emptyProps(),
    'Upsert Job':   props<{ job: Job }>(),
    'Stream Error': props<{ error: string }>(),
    'Toggle Dock':  emptyProps(),
    'Close Dock':   emptyProps(),
  },
});
