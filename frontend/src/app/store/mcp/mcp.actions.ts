import { createActionGroup, emptyProps, props } from '@ngrx/store';
import type { McpConfig } from '@photofant/models';

export const mcpActions = createActionGroup({
  source: 'MCP',
  events: {
    'Load Config':         emptyProps(),
    'Load Config Success': props<{ config: McpConfig }>(),
    'Load Config Failure': props<{ error: string }>(),
    'Save Config':         props<{ config: McpConfig }>(),
    'Save Config Success': props<{ config: McpConfig }>(),
    'Save Config Failure': props<{ error: string }>(),
  },
});
