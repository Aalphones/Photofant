import { createEntityAdapter, type EntityAdapter, type EntityState } from '@ngrx/entity';
import { createFeature, createReducer, on } from '@ngrx/store';
import type { Collection, CollectionDetail } from '@photofant/models';
import { collectionsActions } from './collections.actions';

export interface CollectionsState extends EntityState<Collection> {
  isLoading: boolean;
  error: string | null;
  detail: CollectionDetail | null;
}

const adapter: EntityAdapter<Collection> = createEntityAdapter<Collection>({
  selectId: (item: Collection) => item.id,
  sortComparer: (a: Collection, b: Collection) => a.name.localeCompare(b.name),
});

const initialState: CollectionsState = adapter.getInitialState({
  isLoading: false,
  error: null,
  detail: null,
});

export const collectionsFeature = createFeature({
  name: 'collections',
  reducer: createReducer(
    initialState,
    on(collectionsActions.load, (state: CollectionsState) => ({ ...state, isLoading: true, error: null })),
    on(collectionsActions.loadSuccess, (state: CollectionsState, { items }) =>
      adapter.setAll(items, { ...state, isLoading: false, error: null })
    ),
    on(collectionsActions.loadFailure, (state: CollectionsState, { error }) => ({
      ...state,
      isLoading: false,
      error,
    })),
    on(collectionsActions.loadDetailSuccess, (state: CollectionsState, { detail }) => ({
      ...state,
      detail,
    })),
    on(collectionsActions.clearDetail, (state: CollectionsState) => ({ ...state, detail: null })),
    on(collectionsActions.createSuccess, (state: CollectionsState, { detail }) =>
      adapter.addOne(detail, { ...state, detail })
    ),
    on(collectionsActions.updateSuccess, (state: CollectionsState, { detail }) =>
      adapter.upsertOne(detail, { ...state, detail })
    ),
    on(collectionsActions.deleteSuccess, (state: CollectionsState, { id }) =>
      adapter.removeOne(id, { ...state, detail: state.detail?.id === id ? null : state.detail })
    ),
  ),
  extraSelectors: ({ selectCollectionsState }) => ({
    ...adapter.getSelectors(selectCollectionsState),
  }),
});
