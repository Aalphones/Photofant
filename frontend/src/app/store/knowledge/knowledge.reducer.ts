import { createEntityAdapter, type EntityAdapter, type EntityState } from '@ngrx/entity';
import { createFeature, createReducer, on } from '@ngrx/store';
import type { DomainDto, EntityDto } from '@photofant/models';
import { knowledgeActions } from './knowledge.actions';

export interface KnowledgeState extends EntityState<DomainDto> {
  domainsLoading: boolean;
  domainsError: string | null;
  isSaving: boolean;
  saveError: string | null;
  lastCreatedEntity: EntityDto | null;
}

const adapter: EntityAdapter<DomainDto> = createEntityAdapter<DomainDto>({
  selectId: (domain: DomainDto) => domain.name,
});

const initialState: KnowledgeState = adapter.getInitialState({
  domainsLoading: false,
  domainsError: null,
  isSaving: false,
  saveError: null,
  lastCreatedEntity: null,
});

export const knowledgeFeature = createFeature({
  name: 'knowledge',
  reducer: createReducer(
    initialState,
    on(knowledgeActions.loadDomains, (state: KnowledgeState) => ({
      ...state,
      domainsLoading: true,
      domainsError: null,
    })),
    on(knowledgeActions.loadDomainsSuccess, (state: KnowledgeState, { domains }) =>
      adapter.setAll(domains, { ...state, domainsLoading: false, domainsError: null })
    ),
    on(knowledgeActions.loadDomainsFailure, (state: KnowledgeState, { error }) => ({
      ...state,
      domainsLoading: false,
      domainsError: error,
    })),
    on(knowledgeActions.createEntity, (state: KnowledgeState) => ({
      ...state,
      isSaving: true,
      saveError: null,
    })),
    on(knowledgeActions.createEntitySuccess, (state: KnowledgeState, { entity }) => ({
      ...state,
      isSaving: false,
      saveError: null,
      lastCreatedEntity: entity,
    })),
    on(knowledgeActions.createEntityFailure, (state: KnowledgeState, { error }) => ({
      ...state,
      isSaving: false,
      saveError: error,
    })),
    on(knowledgeActions.resetCreateEntityState, (state: KnowledgeState) => ({
      ...state,
      isSaving: false,
      saveError: null,
      lastCreatedEntity: null,
    })),
  ),
  extraSelectors: ({ selectKnowledgeState }) => ({
    ...adapter.getSelectors(selectKnowledgeState),
  }),
});
