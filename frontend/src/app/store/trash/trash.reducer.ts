import { createEntityAdapter, type EntityAdapter, type EntityState } from '@ngrx/entity';
import { createFeature, createReducer, on } from '@ngrx/store';
import type { AssetDto } from '@photofant/models';
import { trashActions } from './trash.actions';

export interface TrashState extends EntityState<AssetDto> {
  isLoading: boolean;
  error: string | null;
}

const adapter: EntityAdapter<AssetDto> = createEntityAdapter<AssetDto>({
  selectId: (asset: AssetDto) => asset.id,
});

const initialState: TrashState = adapter.getInitialState({
  isLoading: false,
  error: null,
});

export const trashFeature = createFeature({
  name: 'trash',
  reducer: createReducer(
    initialState,
    on(trashActions.load, (state: TrashState) => ({ ...state, isLoading: true, error: null })),
    on(trashActions.loadSuccess, (state: TrashState, { items }) =>
      adapter.setAll(items, { ...state, isLoading: false, error: null })
    ),
    on(trashActions.loadFailure, (state: TrashState, { error }) => ({ ...state, isLoading: false, error })),
    on(trashActions.restoreSuccess, (state: TrashState, { id }) => adapter.removeOne(id, state)),
    on(trashActions.purgeSuccess, (state: TrashState, { id }) => adapter.removeOne(id, state)),
    on(trashActions.emptySuccess, (state: TrashState) => adapter.removeAll(state)),
    on(
      trashActions.restoreFailure,
      trashActions.purgeFailure,
      trashActions.emptyFailure,
      (state: TrashState, { error }) => ({ ...state, error })
    ),
  ),
  extraSelectors: ({ selectTrashState }) => ({
    ...adapter.getSelectors(selectTrashState),
  }),
});
