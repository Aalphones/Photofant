import { createActionGroup, emptyProps, props } from '@ngrx/store';
import type { ComfyUIConfig, ComfyUIWorkflow, WorkflowInput, WorkflowParam } from '@photofant/models';

export const comfyuiActions = createActionGroup({
  source: 'ComfyUI',
  events: {
    'Load Config':          emptyProps(),
    'Load Config Success':  props<{ config: ComfyUIConfig }>(),
    'Load Config Failure':  props<{ error: string }>(),
    'Save Config':          props<{ config: ComfyUIConfig }>(),
    'Save Config Success':  props<{ config: ComfyUIConfig }>(),
    'Save Config Failure':  props<{ error: string }>(),
    'Test Connection':         emptyProps(),
    'Test Connection Success': props<{ ok: boolean; detail: string }>(),
    'Test Connection Failure': props<{ error: string }>(),
    'Clear Test Result':    emptyProps(),

    'Load Workflows':          emptyProps(),
    'Load Workflows Success':  props<{ workflows: ComfyUIWorkflow[] }>(),
    'Load Workflows Failure':  props<{ error: string }>(),
    'Create Workflow':         props<{ file: File; name: string; category: string }>(),
    'Create Workflow Success':  props<{ workflow: ComfyUIWorkflow }>(),
    'Create Workflow Failure':  props<{ error: string }>(),
    'Update Workflow':         props<{ workflowId: string; patch: { name?: string; category?: string; inputs?: WorkflowInput[]; params?: WorkflowParam[] } }>(),
    'Update Workflow Success':  props<{ workflow: ComfyUIWorkflow }>(),
    'Update Workflow Failure':  props<{ error: string }>(),
    'Delete Workflow':         props<{ workflowId: string }>(),
    'Delete Workflow Success':  props<{ workflowId: string }>(),
    'Delete Workflow Failure':  props<{ error: string }>(),
    'Duplicate Workflow':       props<{ workflowId: string }>(),
    'Duplicate Workflow Success': props<{ workflow: ComfyUIWorkflow }>(),
    'Duplicate Workflow Failure': props<{ error: string }>(),
    'Redetect Inputs':         props<{ workflowId: string }>(),
    'Redetect Inputs Success': props<{ workflow: ComfyUIWorkflow }>(),
    'Redetect Inputs Failure': props<{ error: string }>(),
    'Select Workflow':         props<{ workflowId: string | null }>(),
    'Clear Workflow Error':    emptyProps(),
  },
});
