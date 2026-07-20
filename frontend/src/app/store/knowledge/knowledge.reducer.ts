import { createEntityAdapter, type EntityAdapter, type EntityState } from '@ngrx/entity';
import { createFeature, createReducer, createSelector, on } from '@ngrx/store';
import type { AiAutonomyDto, DomainDto, EntityDto, KnowledgeImportResult, TaskDto } from '@photofant/models';
import { knowledgeActions } from './knowledge.actions';

export interface TasksState extends EntityState<TaskDto> {
  loading: boolean;
  error: string | null;
}

// Dritter Adapter im selben Feature-State (analog `TasksState`) — die Wissen-Liste
// (Übersicht + Nachschlagen fürs Edit-Prefill der Aufgabe "Entity noch ohne Inhalt").
export interface EntityListState extends EntityState<EntityDto> {
  loading: boolean;
  error: string | null;
}

export interface KnowledgeState extends EntityState<DomainDto> {
  domainsLoading: boolean;
  domainsError: string | null;
  isSaving: boolean;
  saveError: string | null;
  lastCreatedEntity: EntityDto | null;
  lastUpdatedEntity: EntityDto | null;
  tasks: TasksState;
  entityList: EntityListState;
  // P27 Phase 2 — KI-Vorschlag im Wizard
  aiAutonomy: AiAutonomyDto | null;
  suggestionJobId: string | null;      // Job, dessen Ergebnis wir aus dem Stream erwarten
  suggestionLoading: boolean;
  suggestionResult: KnowledgeImportResult | null;
  suggestionError: string | null;
}

const adapter: EntityAdapter<DomainDto> = createEntityAdapter<DomainDto>({
  selectId: (domain: DomainDto) => domain.name,
});

// Zweiter Adapter im selben Feature-State (FINDINGS.md P23 Phase 3) — Tasks sind
// keine Domänen, brauchen aber dieselbe by-id-Lookup-Semantik für resolve/dismiss.
const taskAdapter: EntityAdapter<TaskDto> = createEntityAdapter<TaskDto>();

const entityAdapter: EntityAdapter<EntityDto> = createEntityAdapter<EntityDto>({
  selectId: (entity: EntityDto) => entity.id,
});

const initialState: KnowledgeState = adapter.getInitialState({
  domainsLoading: false,
  domainsError: null,
  isSaving: false,
  saveError: null,
  lastCreatedEntity: null,
  lastUpdatedEntity: null,
  tasks: taskAdapter.getInitialState({ loading: false, error: null }),
  entityList: entityAdapter.getInitialState({ loading: false, error: null }),
  aiAutonomy: null,
  suggestionJobId: null,
  suggestionLoading: false,
  suggestionResult: null,
  suggestionError: null,
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
    on(knowledgeActions.loadEntities, (state: KnowledgeState) => ({
      ...state,
      entityList: { ...state.entityList, loading: true, error: null },
    })),
    on(knowledgeActions.loadEntitiesSuccess, (state: KnowledgeState, { entities }) => ({
      ...state,
      entityList: entityAdapter.setAll(entities, { ...state.entityList, loading: false, error: null }),
    })),
    on(knowledgeActions.loadEntitiesFailure, (state: KnowledgeState, { error }) => ({
      ...state,
      entityList: { ...state.entityList, loading: false, error },
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
      entityList: entityAdapter.upsertOne(entity, state.entityList),
    })),
    on(knowledgeActions.createEntityFailure, (state: KnowledgeState, { error }) => ({
      ...state,
      isSaving: false,
      saveError: error,
    })),
    on(knowledgeActions.updateEntity, (state: KnowledgeState) => ({
      ...state,
      isSaving: true,
      saveError: null,
    })),
    on(knowledgeActions.updateEntitySuccess, (state: KnowledgeState, { entity }) => ({
      ...state,
      isSaving: false,
      saveError: null,
      lastUpdatedEntity: entity,
      entityList: entityAdapter.upsertOne(entity, state.entityList),
    })),
    on(knowledgeActions.updateEntityFailure, (state: KnowledgeState, { error }) => ({
      ...state,
      isSaving: false,
      saveError: error,
    })),
    on(knowledgeActions.resetCreateEntityState, (state: KnowledgeState) => ({
      ...state,
      isSaving: false,
      saveError: null,
      lastCreatedEntity: null,
      lastUpdatedEntity: null,
    })),
    on(knowledgeActions.loadTasks, (state: KnowledgeState) => ({
      ...state,
      tasks: { ...state.tasks, loading: true, error: null },
    })),
    on(knowledgeActions.loadTasksSuccess, (state: KnowledgeState, { tasks }) => ({
      ...state,
      tasks: taskAdapter.setAll(tasks, { ...state.tasks, loading: false, error: null }),
    })),
    on(knowledgeActions.loadTasksFailure, (state: KnowledgeState, { error }) => ({
      ...state,
      tasks: { ...state.tasks, loading: false, error },
    })),
    // resolve/dismiss laden nur offene Tasks — nach dem Statuswechsel fällt der
    // Task aus der Liste (kein zweiter Load nötig, gleiche Idee wie resolveDupePair).
    on(knowledgeActions.resolveTaskSuccess, (state: KnowledgeState, { task }) => ({
      ...state,
      tasks: taskAdapter.removeOne(task.id, state.tasks),
    })),
    on(knowledgeActions.resolveTaskFailure, (state: KnowledgeState, { error }) => ({
      ...state,
      tasks: { ...state.tasks, error },
    })),
    on(knowledgeActions.dismissTaskSuccess, (state: KnowledgeState, { task }) => ({
      ...state,
      tasks: taskAdapter.removeOne(task.id, state.tasks),
    })),
    on(knowledgeActions.dismissTaskFailure, (state: KnowledgeState, { error }) => ({
      ...state,
      tasks: { ...state.tasks, error },
    })),
    on(knowledgeActions.loadAiAutonomySuccess, (state: KnowledgeState, { autonomy }) => ({
      ...state,
      aiAutonomy: autonomy,
    })),
    // Anfrage läuft: warten, bis der Job-Stream das Ergebnis liefert (suggestionLoading
    // bleibt auch nach dem Success-Ack an, bis der Job fertig ist — der Success trägt nur
    // die Job-Id, noch nicht den Vorschlag).
    on(knowledgeActions.requestImportSuggestion, (state: KnowledgeState) => ({
      ...state,
      suggestionLoading: true,
      suggestionError: null,
      suggestionResult: null,
      suggestionJobId: null,
    })),
    on(knowledgeActions.requestImportSuggestionSuccess, (state: KnowledgeState, { jobId }) => ({
      ...state,
      suggestionJobId: jobId,
    })),
    on(knowledgeActions.requestImportSuggestionFailure, (state: KnowledgeState, { error }) => ({
      ...state,
      suggestionLoading: false,
      suggestionError: error,
      suggestionJobId: null,
    })),
    on(knowledgeActions.importSuggestionReady, (state: KnowledgeState, { result }) => ({
      ...state,
      suggestionLoading: false,
      suggestionResult: result,
      suggestionJobId: null,
    })),
    on(knowledgeActions.importSuggestionFailed, (state: KnowledgeState, { error }) => ({
      ...state,
      suggestionLoading: false,
      suggestionError: error,
      suggestionJobId: null,
    })),
    on(knowledgeActions.resetImportSuggestion, (state: KnowledgeState) => ({
      ...state,
      suggestionLoading: false,
      suggestionResult: null,
      suggestionError: null,
      suggestionJobId: null,
    })),
  ),
  extraSelectors: ({ selectKnowledgeState }) => {
    const selectTasksState = createSelector(selectKnowledgeState, (state: KnowledgeState) => state.tasks);
    const { selectAll: selectAllTasks } = taskAdapter.getSelectors(selectTasksState);
    const selectEntityListState = createSelector(selectKnowledgeState, (state: KnowledgeState) => state.entityList);
    const { selectAll: selectAllEntities, selectEntities: selectEntityDictionary } =
      entityAdapter.getSelectors(selectEntityListState);
    return {
      ...adapter.getSelectors(selectKnowledgeState),
      selectAllTasks,
      selectTasksLoading: createSelector(selectTasksState, (tasks: TasksState) => tasks.loading),
      selectTasksError: createSelector(selectTasksState, (tasks: TasksState) => tasks.error),
      selectAllEntities,
      selectEntityDictionary,
      selectEntitiesLoading: createSelector(selectEntityListState, (state: EntityListState) => state.loading),
      selectEntitiesError: createSelector(selectEntityListState, (state: EntityListState) => state.error),
    };
  },
});
