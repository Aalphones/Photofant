import { createEntityAdapter, type EntityAdapter, type EntityState } from '@ngrx/entity';
import { createFeature, createReducer, on } from '@ngrx/store';
import type { TagListItem } from '@photofant/models';
import { tagsActions } from './tags.actions';

export interface TagsState extends EntityState<TagListItem> {
  isLoading: boolean;
  error: string | null;
}

const adapter: EntityAdapter<TagListItem> = createEntityAdapter<TagListItem>({
  selectId: (item: TagListItem) => item.id,
  sortComparer: (a: TagListItem, b: TagListItem) => b.count - a.count,
});

const initialState: TagsState = adapter.getInitialState({
  isLoading: false,
  error: null,
});

export const tagsFeature = createFeature({
  name: 'tags',
  reducer: createReducer(
    initialState,
    on(tagsActions.load, (state: TagsState) => ({ ...state, isLoading: true, error: null })),
    on(tagsActions.loadSuccess, (state: TagsState, { items }) =>
      adapter.setAll(items, { ...state, isLoading: false, error: null })
    ),
    on(tagsActions.loadFailure, (state: TagsState, { error }) => ({
      ...state,
      isLoading: false,
      error,
    })),
    on(tagsActions.renameSuccess, (state: TagsState, { item }) =>
      adapter.updateOne({ id: item.id, changes: item }, state)
    ),
    on(tagsActions.mergeSuccess, (state: TagsState) => state),
    on(tagsActions.bulkTagSuccess, (state: TagsState) => state),
  ),
  extraSelectors: ({ selectTagsState }) => ({
    ...adapter.getSelectors(selectTagsState),
  }),
});
