import { knowledgeFeature } from './knowledge.reducer';

const {
  selectAll: selectDomains,
  selectDomainsLoading,
  selectDomainsError,
  selectIsSaving,
  selectSaveError,
  selectLastCreatedEntity,
  selectLastUpdatedEntity,
  selectAllTasks,
  selectTasksLoading,
  selectTasksError,
  selectAllEntities,
  selectEntityDictionary,
  selectEntitiesLoading,
  selectEntitiesError,
} = knowledgeFeature;

export const knowledgeSelectors = {
  selectDomains,
  selectDomainsLoading,
  selectDomainsError,
  selectIsSaving,
  selectSaveError,
  selectLastCreatedEntity,
  selectLastUpdatedEntity,
  selectAllTasks,
  selectTasksLoading,
  selectTasksError,
  selectAllEntities,
  selectEntityDictionary,
  selectEntitiesLoading,
  selectEntitiesError,
};
