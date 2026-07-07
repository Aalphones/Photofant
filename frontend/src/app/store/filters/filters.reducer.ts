import { createFeature, createReducer, on } from '@ngrx/store';
import type { Density, MediaType, ReverseSearchState, SortKey, SortOrder } from '@photofant/models';
import { searchActions } from '../search/search.actions';
import { filtersActions } from './filters.actions';

interface FiltersState {
  sort: SortKey;
  order: SortOrder;
  density: Density;
  favourite: boolean | null;
  sources: string[];
  qualityMin: number;
  tagIds: number[];
  collectionId: number | null;
  personId: number | null;
  framings: string[];
  hasFaces: boolean | null;
  mediaType: MediaType;
  classificationLabelIds: number[];
  // Reverse-Image-Filter (P36): geordnete Trefferliste + Quell-Vorschau, oder null
  // wenn der Modus nicht aktiv ist. Exklusiv zu den übrigen Filtern (siehe unten).
  reverseSearch: ReverseSearchState | null;
}

// Die inhaltlichen Filter (nicht Ansicht-Präferenzen wie Sort/Density/MediaType).
// Wird beim „Alle entfernen" und beim Aktivieren des Reverse-Modus zurückgesetzt.
type ContentFilters = Pick<
  FiltersState,
  | 'favourite' | 'sources' | 'qualityMin' | 'tagIds' | 'collectionId'
  | 'personId' | 'framings' | 'hasFaces' | 'classificationLabelIds' | 'reverseSearch'
>;

function clearedContentFilters(): ContentFilters {
  return {
    favourite: null,
    sources: [],
    qualityMin: 0,
    tagIds: [],
    collectionId: null,
    personId: null,
    framings: [],
    hasFaces: null,
    classificationLabelIds: [],
    reverseSearch: null,
  };
}

const initialState: FiltersState = {
  sort: 'date',
  order: 'desc',
  density: 'md',
  ...clearedContentFilters(),
  mediaType: 'photos',
};

export const filtersFeature = createFeature({
  name: 'filters',
  reducer: createReducer(
    initialState,
    on(filtersActions.setSort, (state: FiltersState, { sort, order }) => ({
      ...state,
      sort,
      order,
    })),
    on(filtersActions.setDensity, (state: FiltersState, { density }) => ({
      ...state,
      density,
    })),
    // Ab hier setzen echte Filter — jeder verlässt den Reverse-Modus (Exklusivität),
    // sonst würden Reverse-Treffer und der neue Filter im Backend verschnitten.
    on(filtersActions.setFavourite, (state: FiltersState, { favourite }) => ({
      ...state,
      favourite,
      reverseSearch: null,
    })),
    on(filtersActions.setSources, (state: FiltersState, { sources }) => ({
      ...state,
      sources,
      reverseSearch: null,
    })),
    on(filtersActions.setQualityMin, (state: FiltersState, { qualityMin }) => ({
      ...state,
      qualityMin,
      reverseSearch: null,
    })),
    on(filtersActions.setTagIds, (state: FiltersState, { tagIds }) => ({
      ...state,
      tagIds,
      reverseSearch: null,
    })),
    on(filtersActions.setCollectionId, (state: FiltersState, { collectionId }) => ({
      ...state,
      collectionId,
      reverseSearch: null,
    })),
    on(filtersActions.setPersonId, (state: FiltersState, { personId }) => ({
      ...state,
      personId,
      reverseSearch: null,
    })),
    on(filtersActions.setFramings, (state: FiltersState, { framings }) => ({
      ...state,
      framings,
      reverseSearch: null,
    })),
    on(filtersActions.setHasFaces, (state: FiltersState, { hasFaces }) => ({
      ...state,
      hasFaces,
      reverseSearch: null,
    })),
    on(filtersActions.setClassificationLabelIds, (state: FiltersState, { classificationLabelIds }) => ({
      ...state,
      classificationLabelIds,
      reverseSearch: null,
    })),
    // Reverse ist Foto-only — der Wechsel auf „Gesichter" beendet den Modus; das Klicken
    // von „Fotos" (auch der bereits aktive) lässt einen laufenden Reverse-Filter stehen.
    on(filtersActions.setMediaType, (state: FiltersState, { mediaType }) => ({
      ...state,
      mediaType,
      reverseSearch: mediaType === 'photos' ? state.reverseSearch : null,
    })),
    on(filtersActions.setReverseSearch, (state: FiltersState, { reverseSearch }) => ({
      ...state,
      ...clearedContentFilters(),
      mediaType: 'photos' as const,
      reverseSearch,
    })),
    on(filtersActions.clearReverseSearch, (state: FiltersState) => ({
      ...state,
      reverseSearch: null,
    })),
    on(filtersActions.clearAllFilters, (state: FiltersState) => ({
      ...state,
      ...clearedContentFilters(),
    })),
    // Cross-Slice: eine neue Text-/Semantik-Suche beendet ebenfalls den Reverse-Modus,
    // damit die getippte Anfrage greift statt mit den Reverse-Treffern verschnitten zu werden.
    on(
      searchActions.setQuery,
      searchActions.setMode,
      searchActions.setSemanticQuery,
      searchActions.clear,
      (state: FiltersState) => ({ ...state, reverseSearch: null }),
    ),
  ),
});
