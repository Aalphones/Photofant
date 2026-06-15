import { createFeature, createReducer, on } from '@ngrx/store';
import type { Density, GroupKey, SortKey, SortOrder } from '@photofant/models';
import { filtersActions } from './filters.actions';

interface FiltersState {
  sort: SortKey;
  order: SortOrder;
  group: GroupKey;
  density: Density;
  favourite: boolean | null;
}

const initialState: FiltersState = {
  sort: 'date',
  order: 'desc',
  group: 'month',
  density: 'md',
  favourite: null,
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
  ),
});
