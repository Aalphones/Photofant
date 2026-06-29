import { createFeature, createReducer, on } from '@ngrx/store';
import type { EditorStep, EditorTargetKind } from '@photofant/models';
import { editorActions } from './editor.actions';

export interface EditorState {
  sessionKey: string | null;
  targetKind: EditorTargetKind | null;
  targetId: number | null;
  originalPreviewUrl: string | null;
  steps: EditorStep[];
  currentSeq: number;
  applying: boolean;
  generating: boolean;
  generativeJobId: string | null;
  error: string | null;
}

const initialState: EditorState = {
  sessionKey: null,
  targetKind: null,
  targetId: null,
  originalPreviewUrl: null,
  steps: [],
  currentSeq: 0,
  applying: false,
  generating: false,
  generativeJobId: null,
  error: null,
};

export const editorFeature = createFeature({
  name: 'editor',
  reducer: createReducer(
    initialState,

    on(editorActions.init, (state: EditorState, { kind, id }): EditorState => ({
      ...state,
      targetKind: kind,
      targetId: id,
      sessionKey: null,
      originalPreviewUrl: null,
      steps: [],
      currentSeq: 0,
      applying: false,
      error: null,
    })),

    on(editorActions.initSuccess, (state: EditorState, { sessionKey, originalPreviewUrl, existingSteps }): EditorState => ({
      ...state,
      sessionKey,
      originalPreviewUrl,
      steps: existingSteps,
      currentSeq: existingSteps.length > 0 ? existingSteps[existingSteps.length - 1]!.seq : 0,
      error: null,
    })),

    on(editorActions.initFailure, (state: EditorState, { error }): EditorState => ({
      ...state,
      error,
    })),

    on(editorActions.applyStep, (state: EditorState): EditorState => ({
      ...state,
      applying: true,
      error: null,
    })),

    on(editorActions.applyStepSuccess, (state: EditorState, { step }): EditorState => {
      // When applying, drop all steps after currentSeq (linear undo: new step replaces forward history)
      const stepsUpToCurrent = state.steps.filter((s: EditorStep) => s.seq <= state.currentSeq);
      return {
        ...state,
        steps: [...stepsUpToCurrent, step],
        currentSeq: step.seq,
        applying: false,
      };
    }),

    on(editorActions.applyStepFailure, (state: EditorState, { error }): EditorState => ({
      ...state,
      applying: false,
      error,
    })),

    on(editorActions.rollback, (state: EditorState): EditorState => ({
      ...state,
      applying: true,
    })),

    on(editorActions.rollbackSuccess, (state: EditorState, { seq }): EditorState => ({
      ...state,
      steps: state.steps.filter((s: EditorStep) => s.seq <= seq),
      currentSeq: seq,
      applying: false,
    })),

    on(editorActions.runGenerative, (state: EditorState): EditorState => ({
      ...state,
      generating: true,
      generativeJobId: null,
      error: null,
    })),

    on(editorActions.runGenerativeSuccess, (state: EditorState, { jobId }): EditorState => ({
      ...state,
      generating: false,
      generativeJobId: jobId,
    })),

    on(editorActions.runGenerativeFailure, (state: EditorState, { error }): EditorState => ({
      ...state,
      generating: false,
      error,
    })),

    on(editorActions.close, (): EditorState => initialState),
  ),
});
