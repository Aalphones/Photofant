import { createActionGroup, emptyProps, props } from '@ngrx/store';
import type { CreateEntityRequest, DomainDto, EntityDto } from '@photofant/models';

export const knowledgeActions = createActionGroup({
  source: 'Knowledge',
  events: {
    'Load Domains':         emptyProps(),
    'Load Domains Success': props<{ domains: DomainDto[] }>(),
    'Load Domains Failure': props<{ error: string }>(),
    'Create Entity':            props<{ request: CreateEntityRequest }>(),
    'Create Entity Success':    props<{ entity: EntityDto }>(),
    'Create Entity Failure':    props<{ error: string }>(),
    'Reset Create Entity State': emptyProps(),
  },
});
