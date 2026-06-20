export type EditorTargetKind = 'instance' | 'face' | 'version';

export interface EditorStep {
  seq: number;
  op: string;
  params: Record<string, unknown>;
  label: string;
  previewUrl: string;
}

export interface CreateSessionResponse {
  session_key: string;
  original_preview_url: string;
}

export interface ApplyStepResponse {
  seq: number;
  preview_url: string;
}

export interface RollbackResponse {
  seq: number;
}
