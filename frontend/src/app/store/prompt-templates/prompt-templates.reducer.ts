import { createFeature, createReducer, on } from '@ngrx/store';
import type { PromptTemplateDto } from '@photofant/models';
import { promptTemplateActions } from './prompt-templates.actions';

export interface PromptTemplateState {
  templates: PromptTemplateDto[];
  loading: boolean;
  error: string | null;
}

const initialState: PromptTemplateState = {
  templates: [],
  loading: false,
  error: null,
};

export const promptTemplateFeature = createFeature({
  name: 'promptTemplates',
  reducer: createReducer(
    initialState,

    on(promptTemplateActions.load, (state: PromptTemplateState): PromptTemplateState => ({
      ...state,
      loading: true,
      error: null,
    })),

    on(promptTemplateActions.loadSuccess, (state: PromptTemplateState, { templates }): PromptTemplateState => ({
      ...state,
      templates,
      loading: false,
    })),

    on(promptTemplateActions.loadFailure, (state: PromptTemplateState, { error }): PromptTemplateState => ({
      ...state,
      loading: false,
      error,
    })),

    on(promptTemplateActions.createSuccess, (state: PromptTemplateState, { template }): PromptTemplateState => ({
      ...state,
      templates: [...state.templates, template],
    })),

    on(promptTemplateActions.updateSuccess, (state: PromptTemplateState, { template }): PromptTemplateState => ({
      ...state,
      templates: state.templates.map((existing: PromptTemplateDto) =>
        existing.id === template.id ? template : existing
      ),
    })),

    on(promptTemplateActions.deleteSuccess, (state: PromptTemplateState, { id }): PromptTemplateState => ({
      ...state,
      templates: state.templates.filter((existing: PromptTemplateDto) => existing.id !== id),
    })),
  ),
});
