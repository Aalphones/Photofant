import { createActionGroup, emptyProps, props } from '@ngrx/store';
import type { EditorStep, EditorTargetKind } from '@photofant/models';

export const editorActions = createActionGroup({
  source: 'Editor',
  events: {
    'Init': props<{ kind: EditorTargetKind; id: number }>(),
    'Init Success': props<{ sessionKey: string; originalPreviewUrl: string; existingSteps: EditorStep[] }>(),
    'Init Failure': props<{ error: string }>(),
    'Apply Step': props<{ op: string; params: Record<string, unknown>; label: string }>(),
    'Apply Step Success': props<{ step: EditorStep }>(),
    'Apply Step Failure': props<{ error: string }>(),
    'Rollback': props<{ toSeq: number }>(),
    'Rollback Success': props<{ seq: number }>(),
    'Close': emptyProps(),
  },
});
