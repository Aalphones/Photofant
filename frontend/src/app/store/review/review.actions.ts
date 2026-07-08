import { createActionGroup, emptyProps, props } from '@ngrx/store';
import type { DupePair, DupeResolution, FaceReviewItem, FaceReviewAction } from '@photofant/models';

export const reviewActions = createActionGroup({
  source: 'Review',
  events: {
    'Load Dupe Pairs':         emptyProps(),
    'Load Dupe Pairs Success': props<{ pairs: DupePair[]; total: number }>(),
    'Load Dupe Pairs Failure': props<{ error: string }>(),
    'Load More Dupe Pairs':         emptyProps(),
    'Load More Dupe Pairs Success': props<{ pairs: DupePair[]; total: number }>(),
    'Load More Dupe Pairs Failure': props<{ error: string }>(),
    'Resolve Dupe Pair':       props<{ itemId: number; resolution: DupeResolution }>(),
    'Resolve Dupe Pair Success': props<{ itemId: number }>(),
    'Resolve Dupe Pair Failure': props<{ error: string }>(),
    'Clear Dupe Candidates':         emptyProps(),
    'Clear Dupe Candidates Success': props<{ deleted: number }>(),
    'Clear Dupe Candidates Failure': props<{ error: string }>(),
    'Trigger Dupe Scan':       emptyProps(),
    'Trigger Dupe Scan Success': props<{ jobId: string }>(),
    'Trigger Dupe Scan Failure': props<{ error: string }>(),
    'Trigger Dupe Scan Selection': props<{ assetIds: number[] }>(),
    'Trigger Dupe Scan Selection Success': props<{ jobId: string }>(),
    'Trigger Dupe Scan Selection Failure': props<{ error: string }>(),
    'Load Face Queue':          emptyProps(),
    'Load Face Queue Success':  props<{ items: FaceReviewItem[] }>(),
    'Load Face Queue Failure':  props<{ error: string }>(),
    'Resolve Face Review':      props<{ faceId: number; action: FaceReviewAction; personId?: number }>(),
    'Resolve Face Review Success': props<{ faceId: number }>(),
    'Resolve Face Review Failure': props<{ error: string }>(),
  },
});
