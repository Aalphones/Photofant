import { createSelector } from '@ngrx/store';
import type { EditorStep } from '@photofant/models';
import type { GenerativeResult } from './editor.reducer';
import { editorFeature } from './editor.reducer';

const {
  selectSessionKey, selectSteps, selectCurrentSeq, selectOriginalPreviewUrl,
  selectApplying, selectError, selectTargetId, selectGenerating, selectGenerativeJobId,
  selectGenerativeResult, selectGenerativeSelected,
} = editorFeature;

const selectCurrentPreviewUrl = createSelector(
  selectSteps,
  selectCurrentSeq,
  selectOriginalPreviewUrl,
  selectGenerativeSelected,
  selectGenerativeResult,
  (
    steps: EditorStep[],
    currentSeq: number,
    originalUrl: string | null,
    generativeSelected: boolean,
    generativeResult: GenerativeResult | null,
  ): string | null => {
    if (generativeSelected && generativeResult) {
      return generativeResult.previewUrl;
    }
    if (currentSeq === 0) {
      return originalUrl;
    }
    const step = steps.find((s: EditorStep) => s.seq === currentSeq);
    return step?.previewUrl ?? null;
  },
);

const selectHasUnsavedSteps = createSelector(
  selectSteps,
  (steps: EditorStep[]): boolean => steps.length > 0,
);

const selectStepsForDisplay = createSelector(
  selectSteps,
  selectCurrentSeq,
  (steps: EditorStep[], currentSeq: number): Array<EditorStep & { isCurrent: boolean }> =>
    steps.map((step: EditorStep) => ({ ...step, isCurrent: step.seq === currentSeq })),
);

export const editorSelectors = {
  ...editorFeature,
  selectCurrentPreviewUrl,
  selectHasUnsavedSteps,
  selectStepsForDisplay,
  selectSessionKey,
  selectSteps,
  selectCurrentSeq,
  selectOriginalPreviewUrl,
  selectApplying,
  selectError,
  selectTargetId,
  selectGenerating,
  selectGenerativeJobId,
  selectGenerativeResult,
  selectGenerativeSelected,
};
