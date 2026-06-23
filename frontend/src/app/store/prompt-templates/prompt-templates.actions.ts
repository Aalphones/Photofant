import { createActionGroup, emptyProps, props } from '@ngrx/store';
import type { PromptTemplateDto, CreatePromptTemplateRequest, UpdatePromptTemplateRequest } from '@photofant/models';

export const promptTemplateActions = createActionGroup({
  source: 'PromptTemplates',
  events: {
    'Load': emptyProps(),
    'Load Success': props<{ templates: PromptTemplateDto[] }>(),
    'Load Failure': props<{ error: string }>(),
    'Create': props<{ request: CreatePromptTemplateRequest }>(),
    'Create Success': props<{ template: PromptTemplateDto }>(),
    'Create Failure': props<{ error: string }>(),
    'Update': props<{ id: number; request: UpdatePromptTemplateRequest }>(),
    'Update Success': props<{ template: PromptTemplateDto }>(),
    'Update Failure': props<{ error: string }>(),
    'Delete': props<{ id: number }>(),
    'Delete Success': props<{ id: number }>(),
    'Delete Failure': props<{ error: string }>(),
  },
});
