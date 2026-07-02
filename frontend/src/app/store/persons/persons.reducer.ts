import { createEntityAdapter, type EntityAdapter, type EntityState } from '@ngrx/entity';
import { createFeature, createReducer, on } from '@ngrx/store';
import type { PersonDto } from '@photofant/models';
import { personsActions } from './persons.actions';

export interface PersonsState extends EntityState<PersonDto> {
  isLoading: boolean;
  isClustering: boolean;
  error: string | null;
}

const adapter: EntityAdapter<PersonDto> = createEntityAdapter<PersonDto>({
  selectId: (person: PersonDto) => person.id,
  sortComparer: (a: PersonDto, b: PersonDto) => {
    if (a.is_unknown !== b.is_unknown) {
      return a.is_unknown ? 1 : -1;
    }
    return b.count - a.count;
  },
});

const initialState: PersonsState = adapter.getInitialState({
  isLoading: false,
  isClustering: false,
  error: null,
});

export const personsFeature = createFeature({
  name: 'persons',
  reducer: createReducer(
    initialState,
    on(personsActions.loadPersons, (state: PersonsState) => ({
      ...state,
      isLoading: true,
      error: null,
    })),
    on(personsActions.loadPersonsSuccess, (state: PersonsState, { persons }) =>
      adapter.setAll(persons, { ...state, isLoading: false, error: null })
    ),
    on(personsActions.loadPersonsFailure, (state: PersonsState, { error }) => ({
      ...state,
      isLoading: false,
      error,
    })),
    on(personsActions.renamePersonSuccess, (state: PersonsState, { person }) =>
      adapter.updateOne({ id: person.id, changes: person }, state)
    ),
    on(personsActions.renamePersonFailure, (state: PersonsState, { error }) => ({
      ...state,
      error,
    })),
    on(personsActions.setPersonGroupSuccess, (state: PersonsState, { person }) =>
      adapter.updateOne({ id: person.id, changes: person }, state)
    ),
    on(personsActions.setPersonGroupFailure, (state: PersonsState, { error }) => ({
      ...state,
      error,
    })),
    on(personsActions.triggerClustering, (state: PersonsState) => ({
      ...state,
      isClustering: true,
      error: null,
    })),
    on(personsActions.triggerClusteringSuccess, (state: PersonsState) => ({
      ...state,
      isClustering: false,
    })),
    on(personsActions.triggerClusteringFailure, (state: PersonsState, { error }) => ({
      ...state,
      isClustering: false,
      error,
    })),
    on(personsActions.createPersonSuccess, (state: PersonsState, { person }) =>
      adapter.addOne(person, state)
    ),
    on(personsActions.createPersonFailure, (state: PersonsState, { error }) => ({
      ...state,
      error,
    })),
  ),
  extraSelectors: ({ selectPersonsState }) => ({
    ...adapter.getSelectors(selectPersonsState),
  }),
});
