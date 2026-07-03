import { createEntityAdapter, type EntityAdapter, type EntityState } from '@ngrx/entity';
import { createFeature, createReducer, on } from '@ngrx/store';
import type { ClassificationCategory, ClassificationLabel } from '@photofant/models';
import { classificationActions } from './classification.actions';

export interface ClassificationState extends EntityState<ClassificationCategory> {
  isLoading: boolean;
  error: string | null;
}

const adapter: EntityAdapter<ClassificationCategory> = createEntityAdapter<ClassificationCategory>({
  selectId: (category: ClassificationCategory) => category.id,
  sortComparer: (a: ClassificationCategory, b: ClassificationCategory) => a.position - b.position,
});

const initialState: ClassificationState = adapter.getInitialState({
  isLoading: false,
  error: null,
});

function withLabels(
  state: ClassificationState,
  categoryId: number,
  updater: (labels: ClassificationLabel[]) => ClassificationLabel[],
): ClassificationState {
  const category = state.entities[categoryId];
  if (category == null) { return state; }
  return adapter.updateOne({ id: categoryId, changes: { labels: updater(category.labels) } }, state);
}

export const classificationFeature = createFeature({
  name: 'classification',
  reducer: createReducer(
    initialState,
    on(classificationActions.load, (state: ClassificationState) => ({ ...state, isLoading: true, error: null })),
    on(classificationActions.loadSuccess, (state: ClassificationState, { categories }) =>
      adapter.setAll(categories, { ...state, isLoading: false, error: null })
    ),
    on(classificationActions.loadFailure, (state: ClassificationState, { error }) => ({
      ...state,
      isLoading: false,
      error,
    })),

    on(classificationActions.createCategorySuccess, (state: ClassificationState, { category }) =>
      adapter.addOne(category, state)
    ),
    on(classificationActions.patchCategorySuccess, (state: ClassificationState, { category }) =>
      adapter.updateOne({ id: category.id, changes: category }, state)
    ),
    on(classificationActions.deleteCategorySuccess, (state: ClassificationState, { id }) =>
      adapter.removeOne(id, state)
    ),

    on(classificationActions.createLabelSuccess, (state: ClassificationState, { label }) =>
      withLabels(state, label.category_id, (labels: ClassificationLabel[]) => [...labels, label])
    ),
    on(classificationActions.patchLabelSuccess, (state: ClassificationState, { label }) =>
      withLabels(state, label.category_id, (labels: ClassificationLabel[]) =>
        labels.map((current: ClassificationLabel) => (current.id === label.id ? label : current))
      )
    ),
    on(classificationActions.deleteLabelSuccess, (state: ClassificationState, { id, categoryId }) =>
      withLabels(state, categoryId, (labels: ClassificationLabel[]) =>
        labels.filter((current: ClassificationLabel) => current.id !== id)
      )
    ),
  ),
  extraSelectors: ({ selectClassificationState }) => ({
    ...adapter.getSelectors(selectClassificationState),
  }),
});
