import { createSelector } from '@ngrx/store';
import type { EditorStep } from '@photofant/models';
import { editorFeature } from './editor.reducer';

const { selectSessionKey, selectSteps, selectCurrentSeq, selectOriginalPreviewUrl, selectApplying, selectError, selectTargetId } = editorFeature;

const selectCurrentPreviewUrl = createSelector(
  selectSteps,
  selectCurrentSeq,
  selectOriginalPreviewUrl,
  (steps: EditorStep[], currentSeq: number, originalUrl: string | null): string | null => {
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
};
