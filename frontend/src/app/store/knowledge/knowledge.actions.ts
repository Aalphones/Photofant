import { createActionGroup, emptyProps, props } from '@ngrx/store';
import type { CreateEntityRequest, DomainDto, EntityDto, TaskDto, UpdateEntityRequest } from '@photofant/models';

export const knowledgeActions = createActionGroup({
  source: 'Knowledge',
  events: {
    'Load Domains':         emptyProps(),
    'Load Domains Success': props<{ domains: DomainDto[] }>(),
    'Load Domains Failure': props<{ error: string }>(),
    'Load Entities':         emptyProps(),
    'Load Entities Success': props<{ entities: EntityDto[] }>(),
    'Load Entities Failure': props<{ error: string }>(),
    'Create Entity':            props<{ request: CreateEntityRequest }>(),
    'Create Entity Success':    props<{ entity: EntityDto }>(),
    'Create Entity Failure':    props<{ error: string }>(),
    'Update Entity':            props<{ entityId: string; patch: UpdateEntityRequest }>(),
    'Update Entity Success':    props<{ entity: EntityDto }>(),
    'Update Entity Failure':    props<{ error: string }>(),
    'Reset Create Entity State': emptyProps(),
    'Load Tasks':            emptyProps(),
    'Load Tasks Success':    props<{ tasks: TaskDto[] }>(),
    'Load Tasks Failure':    props<{ error: string }>(),
    'Resolve Task':          props<{ taskId: number }>(),
    'Resolve Task Success':  props<{ task: TaskDto }>(),
    'Resolve Task Failure':  props<{ error: string }>(),
    'Dismiss Task':          props<{ taskId: number }>(),
    'Dismiss Task Success':  props<{ task: TaskDto }>(),
    'Dismiss Task Failure':  props<{ error: string }>(),
  },
});
