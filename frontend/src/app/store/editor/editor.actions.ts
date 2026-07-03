import { createActionGroup, emptyProps, props } from '@ngrx/store';
import type { DefaultRunTask, EditorStep, EditorTargetKind, ResolutionRun, SaveMode, VersionDto } from '@photofant/models';

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
    // Final-Render + speichern. mode entscheidet overwrite vs. neue Kopie;
    // bei reinen Orientierungs-Sessions überschreibt das Backend die Quelle direkt.
    'Save': props<{ mode: SaveMode }>(),
    'Save Success': props<{ version: VersionDto }>(),
    'Save Failure': props<{ error: string }>(),
    // Generativer Run über den Default-Run-Endpunkt (Edit / Inpaint / Upscale).
    // task bestimmt, welcher Default-Workflow aus den Einstellungen verwendet wird.
    // imageSlotKey = der Bild-Slot des Workflows, an den das Editor-Asset gebunden wird.
    // maskDataUrl gesetzt → Inpaint (Backend bettet die Maske als Alpha ins Upload-PNG).
    'Run Generative': props<{
      task: DefaultRunTask;
      imageSlotKey: string;
      prompt: string | null;
      resolution: ResolutionRun | null;
      maskDataUrl: string | null;
    }>(),
    'Run Generative Success': props<{ jobId: string }>(),
    'Run Generative Done': props<{ versionId: number; previewUrl: string; thumbnailUrl: string }>(),
    'Run Generative Failure': props<{ error: string }>(),
    'Select Generative Result': emptyProps(),
    'Close': emptyProps(),
  },
});
