import { createActionGroup, emptyProps, props } from '@ngrx/store';
import type { ModelDto, CapabilitiesDto } from '@photofant/models';

export const modelsActions = createActionGroup({
  source: 'Models',
  events: {
    'Load Models':               emptyProps(),
    'Load Models Success':       props<{ models: ModelDto[] }>(),
    'Load Models Failure':       props<{ error: string }>(),
    'Load Capabilities':         emptyProps(),
    'Load Capabilities Success': props<{ capabilities: CapabilitiesDto }>(),
    'Load Capabilities Failure': props<{ error: string }>(),
    'Load Config':               emptyProps(),
    'Load Config Success':       props<{ modelsDir: string }>(),
    'Load Config Failure':       props<{ error: string }>(),
    'Download Model':            props<{ manifestId: string; licenseAck: boolean }>(),
    'Download Model Success':    props<{ jobId: string; manifestId: string }>(),
    'Download Model Failure':    props<{ manifestId: string; error: string }>(),
    'Register Local':            props<{ manifestId: string; path: string }>(),
    'Register Local Success':    props<{ model: ModelDto }>(),
    'Register Local Failure':    props<{ manifestId: string; error: string; code: string }>(),
    'Clear Bind Error':          emptyProps(),
    'Download Job Completed':    props<{ manifestId: string }>(),
    'Download Job Failed':       props<{ manifestId: string; error: string }>(),
    'Delete Model':              props<{ manifestId: string }>(),
    'Delete Model Success':      props<{ manifestId: string }>(),
    'Delete Model Failure':      props<{ error: string }>(),
    'Update Models Dir':         props<{ path: string }>(),
    'Update Models Dir Success': props<{ modelsDir: string }>(),
    'Update Models Dir Failure': props<{ error: string }>(),
  },
});
