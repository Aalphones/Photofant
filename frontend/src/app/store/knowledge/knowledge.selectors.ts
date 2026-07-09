import { knowledgeFeature } from './knowledge.reducer';

const {
  selectAll: selectDomains,
  selectDomainsLoading,
  selectDomainsError,
  selectIsSaving,
  selectSaveError,
  selectLastCreatedEntity,
} = knowledgeFeature;

export const knowledgeSelectors = {
  selectDomains,
  selectDomainsLoading,
  selectDomainsError,
  selectIsSaving,
  selectSaveError,
  selectLastCreatedEntity,
};
