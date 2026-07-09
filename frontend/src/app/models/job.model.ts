export const JOB_STATES = ['queued', 'running', 'done', 'error'] as const;
export type JobState = typeof JOB_STATES[number];

export const JOB_KINDS = ['demo', 'import', 'scan', 'thumbnail', 'thumbnail_rebuild', 'tag', 'face', 'caption', 'download', 'download_model', 'backup', 'reconcile', 'rebuild', 'tagging', 'captioning', 'embedding', 'heuristics', 'rerun', 'reevaluate', 'comfyui_run', 'captions', 'knowledge_patch'] as const;
export type JobKind = typeof JOB_KINDS[number];

export interface Job {
  id: string;
  kind: JobKind;
  label: string;
  progress: number;
  state: JobState;
  error: string | null;
}
