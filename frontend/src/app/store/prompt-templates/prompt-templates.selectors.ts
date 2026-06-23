import { promptTemplateFeature } from './prompt-templates.reducer';

const { selectTemplates, selectLoading, selectError } = promptTemplateFeature;

export const promptTemplateSelectors = {
  ...promptTemplateFeature,
  selectTemplates,
  selectLoading,
  selectError,
};
