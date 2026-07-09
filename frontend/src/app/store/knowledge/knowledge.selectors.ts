import { knowledgeFeature } from './knowledge.reducer';

const {
  selectAll: selectDomains,
  selectDomainsLoading,
  selectDomainsError,
  selectIsSaving,
  selectSaveError,
  selectLastCreatedEntity,
  selectAllTasks,
  selectTasksLoading,
  selectTasksError,
} = knowledgeFeature;

export const knowledgeSelectors = {
  selectDomains,
  selectDomainsLoading,
  selectDomainsError,
  selectIsSaving,
  selectSaveError,
  selectLastCreatedEntity,
  selectAllTasks,
  selectTasksLoading,
  selectTasksError,
};
