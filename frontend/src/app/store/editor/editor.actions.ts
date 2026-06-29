import { createActionGroup, emptyProps, props } from '@ngrx/store';
import type { EditorStep, EditorTargetKind, ResolutionRun } from '@photofant/models';

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
    // Generativer Run über ComfyUI (Edit / Inpaint / Upscale).
    // imageSlotKey = der Bild-Slot des Workflows, an den das Editor-Asset gebunden wird.
    // maskDataUrl gesetzt → Inpaint (Backend bettet die Maske als Alpha ins Upload-PNG).
    'Run Generative': props<{
      workflowKey: string;
      imageSlotKey: string;
      prompt: string | null;
      resolution: ResolutionRun | null;
      maskDataUrl: string | null;
    }>(),
    'Run Generative Success': props<{ jobId: string }>(),
    'Run Generative Failure': props<{ error: string }>(),
    'Close': emptyProps(),
  },
});
