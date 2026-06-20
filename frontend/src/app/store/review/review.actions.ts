import { createActionGroup, emptyProps, props } from '@ngrx/store';
import type { DupePair, DupeResolution } from '@photofant/models';

export const reviewActions = createActionGroup({
  source: 'Review',
  events: {
    'Load Dupe Pairs':         emptyProps(),
    'Load Dupe Pairs Success': props<{ pairs: DupePair[] }>(),
    'Load Dupe Pairs Failure': props<{ error: string }>(),
    'Resolve Dupe Pair':       props<{ itemId: number; resolution: DupeResolution }>(),
    'Resolve Dupe Pair Success': props<{ itemId: number }>(),
    'Resolve Dupe Pair Failure': props<{ error: string }>(),
    'Trigger Dupe Scan':       emptyProps(),
    'Trigger Dupe Scan Success': props<{ jobId: string }>(),
    'Trigger Dupe Scan Failure': props<{ error: string }>(),
  },
});
