import { createFeature, createReducer, on } from '@ngrx/store';
import type { SearchMode } from '@photofant/models';
import { searchActions } from './search.actions';

interface SearchState {
  q: string;
  mode: SearchMode;
}

const initialState: SearchState = {
  q: '',
  mode: 'text',
};

export const searchFeature = createFeature({
  name: 'search',
  reducer: createReducer(
    initialState,
    // Freitext-Eingabe (Tippen) verlässt sich implizit auf den Modus 'text' — ohne
    // diesen Reset bleibt ein einmal per setSemanticQuery gesetzter 'semantic'-Modus
    // für den Rest der Session hängen und jede weitere Eingabe embedded unbemerkt via CLIP.
    on(searchActions.setQuery,          (state: SearchState, { q })    => ({ ...state, q, mode: 'text' as const })),
    on(searchActions.setMode,           (state: SearchState, { mode }) => ({ ...state, mode, q: '' })),
    on(searchActions.setSemanticQuery,  (state: SearchState, { q })    => ({ ...state, mode: 'semantic' as const, q })),
    on(searchActions.clear,             (state: SearchState)            => ({ ...state, q: '', mode: 'text' as const })),
  ),
});
