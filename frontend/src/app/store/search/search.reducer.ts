import { createFeature, createReducer, on } from '@ngrx/store';
import type { SearchMode } from '@photofant/models';
import { searchActions } from './search.actions';

interface SearchState {
  q: string;
  mode: SearchMode;
}

const initialState: SearchState = {
  q: '',
  mode: 'tags',
};

export const searchFeature = createFeature({
  name: 'search',
  reducer: createReducer(
    initialState,
    on(searchActions.setQuery, (state: SearchState, { q }) => ({ ...state, q })),
    on(searchActions.setMode,  (state: SearchState, { mode }) => ({ ...state, mode, q: '' })),
    on(searchActions.clear,    (state: SearchState) => ({ ...state, q: '' })),
  ),
});
