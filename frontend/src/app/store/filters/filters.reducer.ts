import { createFeature, createReducer, on } from '@ngrx/store';
import type { Density, GroupKey, SortKey, SortOrder } from '@photofant/models';
import { filtersActions } from './filters.actions';

interface FiltersState {
  sort: SortKey;
  order: SortOrder;
  group: GroupKey;
  density: Density;
  favourite: boolean | null;
  sources: string[];
  qualityMin: number;
  tagIds: number[];
  collectionId: number | null;
}

const initialState: FiltersState = {
  sort: 'date',
  order: 'desc',
  group: 'month',
  density: 'md',
  favourite: null,
  sources: [],
  qualityMin: 0,
  tagIds: [],
  collectionId: null,
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
    on(filtersActions.setGroup, (state: FiltersState, { group }) => ({
      ...state,
      group,
    })),
    on(filtersActions.setDensity, (state: FiltersState, { density }) => ({
      ...state,
      density,
    })),
    on(filtersActions.setFavourite, (state: FiltersState, { favourite }) => ({
      ...state,
      favourite,
    })),
    on(filtersActions.setSources, (state: FiltersState, { sources }) => ({
      ...state,
      sources,
    })),
    on(filtersActions.setQualityMin, (state: FiltersState, { qualityMin }) => ({
      ...state,
      qualityMin,
    })),
    on(filtersActions.setTagIds, (state: FiltersState, { tagIds }) => ({
      ...state,
      tagIds,
    })),
    on(filtersActions.setCollectionId, (state: FiltersState, { collectionId }) => ({
      ...state,
      collectionId,
    })),
    on(filtersActions.clearAllFilters, (state: FiltersState) => ({
      ...state,
      favourite: null,
      sources: [],
      qualityMin: 0,
      tagIds: [],
      collectionId: null,
    })),
  ),
});
